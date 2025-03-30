# Card Market to Lex Office Script

This application can be used to import invoices into Lex Office by providing a .csv file from cardmarket. Cardmarket is a platform for buying and selling "Magic the Gathering" playing cards.

## Requirements for Usage

The tool is designed for execution in an windows environment. A python and Taskfile installation is required.

To start the script, follow the steps:

1. Downlaod the project
2. Install Taskfile (see corresponding section in this README.md)
3. Install Python  (see corresponding section in this README.md)
3. Run command `task create-bat`
4. Copy the created file `CardmarketToLexoffice.bat` to a location you like
5. Double click on it, to start the script

### Install Taskfile

Taskfile is used to simplify the usage of the application. To install Taskfile run the following command in your terminal.

For Mac:

```bash
curl -sSL https://taskfile.dev/install.sh | sh
```

For Windows:
```bash
winget install Task.Task
```

### Install Python

Execute in cmd on Windows

```bash
winget install Python.Python.3.13
```

## Requirements for development

### Install Taskfile

Taskfile is used to simplify the usage of the application. To install Taskfile run the following command in your terminal.

For Mac:

```bash
curl -sSL https://taskfile.dev/install.sh | sh
```

For Windows:
```bash
winget install Task.Task
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

#General information about the API can be found here: https://developers.lexoffice.io/docs/?shell#lexoffice-api-documentation