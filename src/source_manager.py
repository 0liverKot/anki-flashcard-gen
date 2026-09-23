from pathlib import Path
from src.md_parser import md_parse
from src.type_aliases import SourceFile

class SourceManager:
    def __init__(self) -> None:
        self.current_source_path = Path(__file__).parent / "notes" / "waves_and_particle_nature_of_light.md"

        self.current_source_json, self.current_source_dict = md_parse(self.current_source_path)


    def get_current_source_dict(self) -> SourceFile:
        return self.current_source_dict

    def get_current_source_json(self) -> str:
        return self.current_source_json
    
    def is_source_valid(self, source: str, debug=False) -> bool:
        for dict in self.current_source_dict:
            if dict.get("source") == source:
                return True

        if debug:
            for dict in self.current_source_dict:
                print(dict.get("source"))
                print(source)
                print("\n")
        return False