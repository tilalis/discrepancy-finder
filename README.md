# discrepancy-finder

# Running the project

## Installation

```bash
pip install .
```

## Configuration

You need to create `.env` file in the root of the project with the following content in your working directory:

```dotenv
DF_DATABASE__URL=some.mongodb.url
DF_DATABASE__USER=theuser
DF_DATABASE__PASSWORD=theuserpassword
DF_DATABASE__NAME=databasename
```

It is also possible to set the environment variables directly in the shell.

## Running the project

```bash
# inside your virtual environment
python3 -m discrepancy_finder <path_to_documents_directory>
```

# Task 1

## Preparation

Starting a simple http server in the documents directory simplifies the process of viewing the documents.

```bash
cd documents
python3 -m http.server
```

### The structure of the documents

* Every document contains an html table with the arbitrary number of rows and columns.
* The table's id attribute contains table id, `<caption>` element contains the table title.
* The header of the table (`<thead>`) contains people's names
* The first column does not have a header and contains the name of the company.
* The intersection of the row and column contains numerical data, sometimes presented as percentages.
* The footer of the table (`<tfoot>`) contains the date and the country of creation
* In some tables, the footer or caption is missing

## Choosing the right tools for a data layer

First thing I need to do is to find the tools to work with mongodb.

I choose the following tools:

* `pymongo`, which is the official mongodb driver for python
* `pydantic-pymongo`, which is a library that allows to use pydantic models with pymongo
* `pydantic-extra-types`, which is a library that provides additional types for pydantic, such as Country

I choose `pydantic-mongo` over `mongoengine` because:

* pydantic is more pythonic
* it is a good idea to separate the presentation from data, so that both can be used independently
* pydantic is more flexible and can be used with other libraries, such as but not limited to FastAPI if in the future
  we'll need to provide an API or publish a library for 3rd party developers

## Defining the data model

Document model is defined in [document.py](src/discrepancy_finder/models/document.py)

Design decisions regarding the data model:

* header is stored as a list of strings
* Document body is its own model, with its own header: `str` field and body: `list[str]` field
* date_of_creation is stored as a datetime object

Discrepancy model is defined in [discrepancy.py](src/discrepancy_finder/models/discrepancy.py)

Design decisions regarding the discrepancy model:

* for now, discrepancy_type is defined as a string, but it can be changed to an enum when implementing the logic for
  Task 2 (I am assuming the for the moment I don't know possible discrepancy types)
* location is a string, redefined as `DiscrepancyLocation` by typing.NewType for typechecking purposes

## Creating configuration

pydantic has another extension called `pydantic-settings`, which allows to define a configuration class that can be used
to store the configuration of the application.

The settings are defined in [settings.py](src/discrepancy_finder/settings.py)

## Logging

For logging, I have chosen `loguru` library, which is a flexible, easy-to-use and zero-configuration logging
library.

## Creating the database

I have created a database called `discrepancy_finder` and two collections called `documents` and `discrepancies`.
Both collections have unique text indexes on the `document_id` and `discrepancy_id` fields.

```mongosh
db.documents.createIndex({'document_id': 'text'}, {unique: true})
db.discrepancies.createIndex({'discrepancy_id': 'text'}, {unique: true})
```

I have also defined a `DocumentRepository` and `DiscrepancyRepository` classes
in [repositories.py](src/discrepancy_finder/models/repositories.py)

In order to get functionality not defined in `AbstractRepository`,
I have created a `AbstractReporitoryWithInsertMany` class that contains `insert_many` method not present in
the `AbstractRepository`.

## Parsing the documents

My first library of choice is `beautifulsoup4`, which is a library that allows to parse HTML and XML documents.

I have created a separate `parse_document` method in [document_parser.py](src/discrepancy_finder/document_parser.py) for
parsing a single document.
This function is then called in `parse` method which iterates over html files in the specified directory and returns a
generator of parsed documents.

# Task 2

## Implementing the DocumentValidator

DocumentValidator class is defined in [validator.py](src/discrepancy_finder/validator.py)

DocumentValidator is an abstract base class that provides default functionality for validators,
for instance -- `create_result` method, which simplifies result creation

By design, the DocumentValidator subclass should validate against one rule.
The checks should be implemented in `validate` method.
DocumentValidator implements Strategy pattern, being a Strategy interface by itself.

In order to not have a big try-except block, I have created a `on_exception` decorator that catches the exception and
controls the return value in case of an exception.

This decorator is parametrized and accepts `return_value` parameter which can be a callable.
If it is a callable, its result is returned on exception.

`validator` module provides `default_on_exception` decorator which is `on_exception`
that returns ValidationResult.ERROR with other default data returned by DocumentValiadtor.

### Default implementation of `validate` method

In DocumentValidator, `validate` method is abstract,
but has a default implementation which returns SUCCESS status and all the information about the validator.

All the DocumentValidator subclasses are expected to return its parent call its parent `validate` on success, instead of
providing the success values by themselves.

It is done intentionally, so that it would be possible to generalize some validation checks, re-use validators
and build a validators hierarchy if necessary.

## Location of the validation result

To describe the location where validation fails, JSONPath is used

## Implementing DiscrepancyFinder

## Implementing the logic for Task 2

In order to simplify things, the logic implementation in Task 1 was not implemented using
design patterns. It was a `main()` method with straightforward control flow.

In Task 2, I have implemented the logic using Chain of Responsibility pattern, where each class is responsible for
a single action within the process parsing the documents and finding discrepancies.

_Initially_ the classes were:

* DirectoryParsingHandler
* DiscrepancyFinderHandler (which is an adapter for DiscrepancyFinder)
* SaveDocumentsHandler
* SaveDiscrepanciesHandler

After initial implementation I have noticed that SaveDocumentsHandler and SaveDiscrepanciesHandler are implementing
the same logic, so I have merged them into a single class called DatabaseInsertHandler.

## Configuration notice for Task 2

In order to simplify things, I have not added configuration for DiscrepancyType and it's parameters.

However, it would not be hard to inherit the DiscrepancyType class from pydantic's BaseModel and by this
make it possible to easily configure discrepancies via environment variables or configuration files.

# Tests

Per my understanding, the tests are beyond the scope of this assignment


