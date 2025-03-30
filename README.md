# Card Market to Lex Office Script

This application can be used to import invoices into Lex Office by providing a .csv file from cardmarket. Cardmarket is a platform for buying and selling "Magic the Gathering" playing cards.


## Installation for Usage on Windows

The tool is designed for execution in an windows environment. To install, execute the script `install.bat`. Further instructions are provided via the cmd output.

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

To run the application, run the following command.

```bash
task run
```

## Lexoffice

General information about the API can be found here: https://developers.lexoffice.io/docs/?shell#lexoffice-api-documentation