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
set CARDMARKET_USERNAME=your_username
set CARDMARKET_PASSWORD=your_password
```

#### Windows - Powershell

```bash
$env:CARDMARKET_USERNAME="your_username"
$env:CARDMARKET_PASSWORD="your_password"
```

#### Mac / Linux

```bash
export CARDMARKET_USERNAME=your_username
export CARDMARKET_PASSWORD=your_password
```

## Usage

To run the application, run the following command.

```bash
task run
```

## Lexoffice

General information about the API can be found here: https://developers.lexoffice.io/docs/?shell#lexoffice-api-documentation