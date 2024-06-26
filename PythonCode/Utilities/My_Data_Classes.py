from dataclasses import dataclass, field, asdict
from typing import Set, List


@dataclass
class CategoryInfo:
    url: str = ""
    faculty_count: int = 0
    department_count: int = 0
    article_count: int = 0
    files: Set[str] = field(default_factory=set)
    faculty: Set[str] = field(default_factory=set)
    departments: Set[str] = field(default_factory=set)
    titles: Set[str] = field(default_factory=set)
    tc_count: int = 0
    tc_list: List[int] = field(default_factory=list)
    citation_average: int = 0

    # this holds the file names associated with articles
    # article_set: Set[str] = field(default_factory=set)

    def to_dict(self) -> dict:
        # Utilize asdict utility from dataclasses, then change sets to lists
        data_dict = asdict(self)

        # Exclude 'files' from the dictionary
        if "files" in data_dict:
            del data_dict["files"]

        # Convert sets to lists for JSON serialization
        for key, value in data_dict.items():
            if isinstance(value, Set):
                data_dict[key] = list(value)
        return data_dict
