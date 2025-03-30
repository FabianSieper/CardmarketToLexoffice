# ToDos

- install_windows.bat erstellen die installiert:
  - python
  - taskfile
  und erstellt auf dem desktop eine .bat zum ausführen des ganzen

# Card Market to Lex Office Script

## Requirements

### Taskfile

Taskfile is used to simplify the usage of the application. To install Taskfile run the following command in your terminal.

```bash
# Ensure curl is installed
command -v curl >/dev/null 2>&1 || { \
  echo "Installing curl..."; \
  if [ "$(uname)" = "Darwin" ]; then \
    brew install curl; \
  elif [ -f /etc/debian_version ]; then \
    sudo apt update && sudo apt install -y curl; \
  elif [ -f /etc/redhat-release ]; then \
    sudo dnf install -y curl; \
  else \
    echo "Please install curl manually."; exit 1; \
  fi \
}

# Install Task
curl -sSL https://taskfile.dev/install.sh | sh
```

### Credentials

For this to work, all credentials have to be stored in the environment of your computer. This can be done in one of the following ways.

#### Windows - CMD

```bash
set LEXOFFICE_API_KEY=your_api_key
```

#### Windows - Powershell

```bash
$env:LEXOFFICE_API_KEY="your_api_key"
```

#### Mac / Linux

```bash
export LEXOFFICE_API_KEY=your_api_key
```

## Usage

To run the application, run the following command.

```bash
task run
```

## Lexoffice

General information about the API can be found here: https://developers.lexoffice.io/docs/?shell#lexoffice-api-documentation