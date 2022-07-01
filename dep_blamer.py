import argparse
import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Optional, Set, Dict, List, IO, Iterable, Callable

import git


def range_intersection(x: range, y: range) -> Optional[range]:
    start = max(x.start, y.start)
    end = min(x.stop, y.stop)
    if start >= end:
        return None
    else:
        return range(start, end)


class DepBlamer:

    def __init__(self, repo_path: Path):
        self.repo: git.Repo = git.Repo(repo_path)

    def blame_range(self, commit: str, file_path: str, start_line: int, end_line: int) -> Set[git.Commit]:
        ret = set()
        for blame_entry in self.repo.blame_incremental(commit, file_path):
            blame_commit = blame_entry.commit
            common_range = range_intersection(range(start_line, end_line + 1), blame_entry.linenos)
            if common_range is not None:
                ret.add(blame_commit)
        return ret


@dataclass(frozen=True)
class Entity:
    path: Path
    id: int
    category: str
    qualified_name: str
    start_line: int
    end_line: int


cached_roots: Set[Path] = set()


def find_ent_path(root_path: Path, qualified_name: str) -> Path:
    global cached_roots
    elts = qualified_name.split(".")
    for elt in elts:
        temp_path = root_path.joinpath(elt)
        temp_java_path = root_path.joinpath(f"{elt}.java")
        if temp_java_path.exists():
            return temp_java_path
        else:
            root_path = temp_path
    raise ValueError(f"{qualified_name} not exists in file system")


def find_ent_path_in_all(root_path: Path, qualified_name: str) -> Path:
    global cached_roots
    for subdir, dirs, files in os.walk(root_path):
        print(subdir)
        try:
            ent_path = find_ent_path(Path(subdir), qualified_name)
            cached_roots.add(Path(subdir))
            return ent_path
        except ValueError:
            continue
    raise ValueError(f"{qualified_name} not exists in file system")


def find_ent_workflow(root_path: Path, qualified_name: str) -> Path:
    global cached_roots
    for root in cached_roots:
        try:
            return find_ent_path(root, qualified_name)
        except ValueError:
            ...
    return find_ent_path_in_all(root_path, qualified_name)


@dataclass
class EntOwnership:
    entity: Entity
    commits: Set[str]


class DepData:
    def __init__(self, repo_path: Path, analyzed_root: Path, dep_file: Path):
        self.repo_path = repo_path
        self.analyzed_root = analyzed_root
        self.dep_obj = json.loads(dep_file.read_text())

    def get_dep_ents(self) -> Set[Entity]:
        ret = set()

        for v in self.dep_obj["variables"]:
            try:
                location = v["location"]
                ret.add(
                    Entity(Path(v["File"]), v["id"], v["category"], v["qualifiedName"], location["startLine"],
                           location["endLine"]))
            except KeyError:
                pass

        return ret


def dump_ownership(ownership_data: List[EntOwnership], fp: IO):
    writer = csv.DictWriter(fp, ["Entity", "category", "id", "file path", "commits"])
    writer.writeheader()
    for d in ownership_data:
        writer.writerow({
            "Entity": (d.entity.qualified_name),
            "category": d.entity.category,
            "id": d.entity.id,
            "file path": d.entity.path,
            "commits": json.dumps([str(c) for c in d.commits])
        })


def collect_all_file(ents: Iterable[Entity]) -> Set[Path]:
    ret = set()
    for ent in ents:
        ret.add(ent.path)
    return ret


@dataclass
class BlameObject:
    commit: str
    start: int
    stop: int


def create_blame_dict(file_set: Set[Path], repo: git.Repo, commit: str) -> Dict[Path, List[BlameObject]]:
    file_blame_dict: Dict[Path, List[BlameObject]] = dict()
    for file_path in file_set:
        file_blame_dict[file_path] = [BlameObject(str(be.commit), be.linenos.start, be.linenos.stop) for be in
                                      repo.blame_incremental(commit, str(file_path))]

    return file_blame_dict


def contain_commit(blame_entries: List[BlameObject], commits: Set[str]) -> bool:
    for entry in blame_entries:
        if str(entry.commit) in commits:
            return True
    return False


def create_blamer(file_blame_dict: Dict[Path, List[BlameObject]]) -> Callable[[Path, int, int], Set[str]]:
    def blame(path: Path, start_line: int, end_line: int) -> Set[str]:
        ret = set()
        for blame_entry in file_blame_dict[path]:
            blame_commit = str(blame_entry.commit)
            common_range = range_intersection(range(start_line, end_line + 1),
                                              range(blame_entry.start, blame_entry.stop))
            if common_range is not None:
                ret.add(blame_commit)
        return ret

    return blame


def load_commits(file_path: Path) -> Set[str]:
    with open(file_path) as file:
        return {line[:-1] for line in file.readlines()}


def dump_blame_dict(blame_dict: Dict[Path, List[BlameObject]], file_name: Path):
    with open(file_name, "w", newline='') as f:
        writer = csv.writer(f)
        for file_path, blame_entries in blame_dict.items():
            entry_list = [(be.commit, be.start, be.stop) for be in blame_entries]
            writer.writerow([str(file_path), json.dumps(entry_list)])


def get_sha(repo_path: Path) -> Optional[str]:
    repo = git.Repo(repo_path)
    return str(repo.head.commit)
    # return next((str(tag) for tag in repo.tags if tag.commit == repo.head.commit), None)


def load_blame_dict(file_path: Path) -> Dict[Path, List[BlameObject]]:
    csv.field_size_limit(500*1024*1024)
    ret: Dict[Path, List[BlameObject]] = dict()
    with open(file_path, "r") as file:
        reader = csv.reader(file)
        for row in reader:
            path = row[0]
            entry_list = json.loads(row[1])
            entry_list = [BlameObject(e[0], e[1], e[2]) for e in entry_list]
            ret[Path(path)] = entry_list

    return ret


def entry():
    start_time = time()
    # analyzed_root = "D:\\Master\\CodeSmell\\Refactor\\frameworks\\base"
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", dest="repo_path", action="store")
    parser.add_argument("--dep", dest="accompany_dep", action="store")
    parser.add_argument("--base_commits", dest="base_commits", action="store")
    parser.add_argument("--only_accompany_commits", dest="only_accompany_commits", action="store")
    parser.add_argument("--blame_cache", dest="blame_cache", action="store")
    args = parser.parse_args()
    analyzed_root = args.repo_path
    # repo_path = Path("D:\\Master\\CodeSmell\\Refactor\\frameworks\\base")
    repo_path = Path(analyzed_root)
    sha = get_sha(repo_path)
    print(f"{sha} @ {analyzed_root}")
    dep_data = DepData(repo_path, Path(analyzed_root), Path(args.accompany_dep))
    current_commit = sha
    ents = dep_data.get_dep_ents()
    ownership_data = []
    only_accompany_commits = load_commits(Path(args.only_accompany_commits))

    file_set = collect_all_file(ents)

    blame_dict_path = Path(f"blame_dict_{Path(analyzed_root).name}_{sha}")

    blame_dict_path.touch(exist_ok=True)
    if args.blame_cache:
        blame_dict = load_blame_dict(Path(args.blame_cache))
    elif blame_dict_path.stat().st_size == 0:
        blame_dict = create_blame_dict(file_set, git.Repo(repo_path), current_commit)
        dump_blame_dict(blame_dict, blame_dict_path)
    else:
        blame_dict = load_blame_dict(blame_dict_path)

    def is_accompany_file(f: Path):
        return contain_commit(blame_dict[f], only_accompany_commits)

    accompany_file_set = set(filter(is_accompany_file, file_set))
    blame = create_blamer(blame_dict)
    for ent in ents:
        print(ent)
        if ent.path not in accompany_file_set:
            continue
        ent_commits = blame(ent.path, ent.start_line, ent.end_line)
        ownership_data.append(EntOwnership(ent, ent_commits))
    with open(f"{Path(analyzed_root).name}_{sha}_ownership.csv", "w", encoding="utf-8", newline="") as f:
        dump_ownership(ownership_data, f)

    # with open(f"{analyzed_root}_ownership_lineageos_{sha}.csv", "w", newline="") as f:
    #     f.writelines(str(f) + "\n" for f in file_set)

    # with open("blame_dict", "wb") as f:
    #     pickle.dump(blame_dict, f)
    end_time = time()
    print(end_time - start_time)


if __name__ == '__main__':
    entry()
