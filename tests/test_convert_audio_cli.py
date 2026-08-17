from convert_audio import build_parser


def test_parser_accepts_input_and_output_types() -> None:
    args = build_parser().parse_args(["--input-type", "mp3", "m4a", "--output-type", "flac"])

    assert args.input_type == ["mp3", "m4a"]
    assert args.output_type == "flac"
