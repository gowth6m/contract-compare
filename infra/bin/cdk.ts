#!/usr/bin/env node
import 'source-map-support/register';
import { BackendStack } from '../lib/backend-stack';
import * as cdk from 'aws-cdk-lib';
import * as dotenv from 'dotenv';
import * as path from 'path';
import { FrontendStack } from '../lib/frontend-stack';

// --------------------------------------------------------------

dotenv.config({ path: path.resolve(__dirname, '..', '..', '.env') });

// --------------------------------------------------------------

const defaultAccountID = '565393066288';
const defaultRegion = 'eu-west-2';
const defaultEnvironment = 'sandbox';

const accountID = process.env.AWS_ACCOUNT_ID || defaultAccountID;
const region = process.env.AWS_REGION || defaultRegion;
const stage = process.env.ENVIRONMENT || defaultEnvironment;
const regionForFrontend = 'us-east-1';

// --------------------------------------------------------------

const app = new cdk.App();

new BackendStack(app, `BackendStack-${stage}`, {
  env: {
    account: accountID,
    region: region,
  },
  stage: stage,
  stackName: `BackendStack-${stage}`,
  description: `Backend stack for ${stage} stage`,
});

new FrontendStack(app, `FrontendStack-${stage}`, {
  env: {
    account: accountID,
    region: regionForFrontend,
  },
  stage: stage,
  stackName: `FrontendStack-${stage}`,
  description: `Frontend stack for ${stage} stage`,
});

app.synth();