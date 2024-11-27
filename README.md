# Contracts Compare

Live demo [here](https://app.sandbox.jurisai.uk)

Video demo [here](https://youtu.be/WwDlyC-LlmM)

## Frontend

The frontend is React application built with Vite, MUI, React Query and Axios.

## Backend

The backend is a FastAPI application built with FastAPI, MongoDB, AWS Services. It provides the API endpoints for the frontend to interact with the database and perform various operations.

## Infrastructure

The infrastructure is managed using AWS CDK. The backend is deployed as zipped Lambda functions and the frontend is deployed as a static website on S3.

## Swagger documentation

View the API documentation [here](https://api.sandbox.jurisai.uk/docs)

## Architecture Diagram

![Preview](https://github.com/gowth6m/contract-compare/blob/main/docs/arch_diagram.png)