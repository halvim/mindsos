"""Console-script entrypoint for the `mindsos` command."""

from mindsos_cli.app import app


def main() -> None:
    app()


if __name__ == "__main__":
    main()
