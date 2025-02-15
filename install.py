import argparse
import platform
import subprocess
import sys


def check_poetry() -> bool:
    """Check if Poetry is installed and install it if not."""
    try:
        subprocess.run(['poetry', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print('Poetry is not installed. Installing Poetry...')

        if platform.system() == 'Windows':
            try:
                subprocess.run([
                    'powershell',
                    '(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | python -'
                ], check=True)
            except subprocess.CalledProcessError:
                print('Failed to install Poetry. Please install it manually.')
                return False
        else:  # Linux/Unix
            try:
                subprocess.run(
                    'curl -sSL https://install.python-poetry.org | python3 -',
                    shell=True,
                    check=True
                )
            except subprocess.CalledProcessError:
                print('Failed to install Poetry. Please install it manually.')
                return False
        return True


def install(args) -> None:
    """Main installation function."""
    if not check_poetry():
        sys.exit(1)

    install_args = []
    if args.gpu:
        print('Installing GPU version...')
        install_args.extend(['-E', 'gpu', '--with', 'gpu', '--no-root'])
    else:
        print('Installing CPU version...')
        install_args.extend(['-E', 'cpu', '--with', 'cpu', '--no-root'])

    if args.test:
        print('Including test dependencies...')
        install_args.extend(['-E', 'test'])

    subprocess.run(['poetry', 'install'] + install_args, check=True)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Install Libb-NLP Text Splitter')
    parser.add_argument('-t', '--test', action='store_true', help='Install test dependencies')
    parser.add_argument('-g', '--gpu', action='store_true', help='Install GPU version')
    args = parser.parse_args()

    try:
        install(args)
        print('Installation completed successfully!')
    except KeyboardInterrupt:
        print('\nInstallation cancelled by user.')
        sys.exit(1)
    except Exception as e:
        print(f'An error occurred during installation: {e}')
        sys.exit(1)


if __name__ == '__main__':
    main()
