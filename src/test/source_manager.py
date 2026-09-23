from src.source_manager import SourceManager


def test_is_source_valid():
    source = "Topic 5: Waves and the Particle Nature of Light > 5.84 Diffraction grating"
    source_manager = SourceManager()

    print(f"Source: {source}\n")

    print("Result")
    print(source_manager.is_source_valid(source, debug=True))



if __name__ == "__main__":
    print("Testing the is_source_valid method\n")
    test_is_source_valid()