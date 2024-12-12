import argparse
import os
import shutil
import sys
from pathlib import Path

from process_pdf import alt_text


def get_config(path: str) -> None:
    if path is None:
        with open(
            os.path.join(Path(__file__).parent.absolute(), "../config.json"),
            "r",
            encoding="utf-8",
        ) as f:
            print(f.read())
    else:
        src = os.path.join(Path(__file__).parent.absolute(), "../config.json")
        dst = path
        shutil.copyfile(src, dst)


def main():
    parser = argparse.ArgumentParser(
        description="Generate summary for tables in PDF",
    )
    parser.add_argument("--name", type=str, default="", help="Pdfix license name")
    parser.add_argument("--key", type=str, default="", help="Pdfix license key")

    subparsers = parser.add_subparsers(dest="subparser")

    # config subparser
    pars_config = subparsers.add_parser(
        "config",
        help="Extract config file for integration",
    )
    pars_config.add_argument(
        "-o",
        "--output",
        type=str,
        help="Output to save the config JSON file. Application output\
              is used if not provided",
    )

    pars_detect = subparsers.add_parser(
        "detect",
        help="Run alternate text description",
    )

    pars_detect.add_argument("-i", "--input", type=str, help="The input PDF file")
    pars_detect.add_argument(
        "-o",
        "--output",
        type=str,
        help="The output PDF file",
    )

    pars_detect.add_argument("--openai", type=str, required=True, help="OpenAI API key")
    pars_detect.add_argument(
        "--tags",
        type=str,
        required=False,
        default="Table",
        help="Regular expression defining the tag name",
    )
    pars_detect.add_argument(
        "--overwrite",
        type=bool,
        default=False,
        help="Overwrite the alt text if it exists",
    )
    pars_detect.add_argument(
        "--lang",
        type=str,
        required=False,
        default="English",
        help="Laguage",
    )

    try:
        args = parser.parse_args()
    except SystemExit as e:
        if e.code == 0:  # This happens when --help is used, exit gracefully
            sys.exit(0)
        print("Failed to parse arguments. Please check the usage and try again.")
        sys.exit(1)

    if args.subparser == "config":
        get_config(args.output)
        sys.exit(0)

    elif args.subparser == "detect":
        if not args.input or not args.output or not args.openai:
            parser.error(
                "The following arguments are required:\
                 -i/--input, -o/--output, --openai",
            )

        input_file = args.input
        output_file = args.output

        if not os.path.isfile(input_file):
            sys.exit(f"Error: The input file '{input_file}' does not exist.")
            return

        if input_file.lower().endswith(".pdf") and output_file.lower().endswith(".pdf"):
            try:
                alt_text(
                    input_file,
                    output_file,
                    args.tags,
                    args.name,
                    args.key,
                    args.openai,
                    args.overwrite,
                    args.lang,
                )
                # print(desc)
            except Exception as e:
                sys.exit("Failed to run table summary {}".format(e))

        else:
            print("Input and output file must be PDF")


if __name__ == "__main__":
    main()
