# Card Market to Lex Office Script

This application can be used to import invoices into Lex Office by providing a .csv file from cardmarket. Cardmarket is a platform for buying and selling "Magic the Gathering" playing cards.

## Requirements for development

### Taskfile

Taskfile is used to simplify the usage of the application. To install Taskfile run the following command in your terminal.

```bash
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