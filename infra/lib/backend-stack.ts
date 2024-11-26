import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as apigatewayv2 from 'aws-cdk-lib/aws-apigatewayv2';
import * as targets from 'aws-cdk-lib/aws-route53-targets';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as acm from 'aws-cdk-lib/aws-certificatemanager';
import * as route53 from 'aws-cdk-lib/aws-route53';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cdk from 'aws-cdk-lib';
import * as path from 'path';

import { Construct } from 'constructs';

import * as dotenv from 'dotenv';

// --------------------------------------------------------------

dotenv.config({ path: path.resolve(__dirname, '..', '..', '.env') });

// --------------------------------------------------------------

export interface BackendProps extends cdk.StackProps {
  readonly stage: string;
  readonly zone?: route53.IHostedZone;
}

// --------------------------------------------------------------

export class BackendStack extends cdk.Stack {

  stage: string;

  constructor(scope: Construct, id: string, props: BackendProps) {
    super(scope, id, props);

    this.stage = props.stage

    const hostedZone = props.zone || route53.HostedZone.fromLookup(this, 'NewHostedZone', {
      domainName: `sandbox.jurisai.uk`
    });

    const secretsForInfra = [
      `arn:aws:secretsmanager:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:secret:backend/base-*`,
      `arn:aws:secretsmanager:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:secret:backend/sqs-*`,
      `arn:aws:secretsmanager:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:secret:backend/s3-*`,
      `arn:aws:secretsmanager:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:secret:backend/websocket-*`,
    ]

    // SQS queue for processing uploaded files
    const sqsQueue = new sqs.Queue(this, 'ContractProcessingQueue', {
      queueName: `${this.stage}-contract-processing-queue`,
      visibilityTimeout: cdk.Duration.seconds(600),
      retentionPeriod: cdk.Duration.days(14),
    });

    // S3 bucket for uploaded files
    const s3Bucket = new s3.Bucket(this, 'UploadedFilesBucket', {
      bucketName: `${this.stage}-uploaded-files-bucket`,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // --------------------------------------------------------------
    // ---------------- LAYERS --------------------------------------
    // --------------------------------------------------------------

    // All python dependencies (built on Amazon Linux 2)
    const dependenciesLayer = new lambda.LayerVersion(this, 'DependenciesLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'dependenciesLayer', 'dependenciesLayer.zip')),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Lambda layer with dependencies for BackendLambda',
    });

    // Shared code between BackendLambda and ProcessUploadedFilesLambda
    const sharedLayer = new lambda.LayerVersion(this, 'SharedLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'sharedLayer', 'sharedLayer.zip')),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_11],
      description: 'Lambda layer with shared code for BackendLambda and ProcessUploadedFilesLambda',
    });

    // --------------------------------------------------------------
    // ---------------- BACKEND LAMBDA ------------------------------
    // --------------------------------------------------------------

    const backendLambda = new lambda.Function(this, 'BackendLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.X86_64,
      handler: 'main.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'backendLambda', 'backendLambda.zip')),
      memorySize: 512,
      timeout: cdk.Duration.seconds(60),
      layers: [dependenciesLayer, sharedLayer],
    });

    backendLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: secretsForInfra,
    }));

    sqsQueue.grantSendMessages(backendLambda);
    s3Bucket.grantReadWrite(backendLambda);

    // --------------------------------------------------------------
    // ---------------- PROCESS FILES LAMBDA ------------------------
    // --------------------------------------------------------------

    const processUploadedFilesLambda = new lambda.Function(this, 'ProcessUploadedFilesLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.X86_64,
      handler: 'process_uploaded_files.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'processUploadedFiles', 'processUploadedFiles.zip')),
      memorySize: 1024,
      timeout: cdk.Duration.seconds(60),
      layers: [dependenciesLayer, sharedLayer],
    });

    processUploadedFilesLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: secretsForInfra,
    }));

    sqsQueue.grantConsumeMessages(processUploadedFilesLambda);
    s3Bucket.grantReadWrite(processUploadedFilesLambda);

    processUploadedFilesLambda.addEventSource(
      new lambdaEventSources.SqsEventSource(sqsQueue, {
        batchSize: 10, // No. of msg processed in 1 lambda execution
      }),
    );

    // --------------------------------------------------------------
    // ---------------- REST API GATEWAY ----------------------------
    // --------------------------------------------------------------

    const certificate = new acm.Certificate(this, 'ApiCertificate', {
      domainName: `api.sandbox.jurisai.uk`,
      validation: acm.CertificateValidation.fromDns(hostedZone)
    });

    const api = new apigateway.LambdaRestApi(this, 'BackendAPI', {
      handler: backendLambda,
      domainName: {
        domainName: `api.sandbox.jurisai.uk`,
        certificate: certificate,
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
      },
      proxy: true,
      integrationOptions: {
        contentHandling: apigateway.ContentHandling.CONVERT_TO_BINARY,
      },
      binaryMediaTypes: [
        'image/jpeg',
        'application/pdf',
        'application/octet-stream',
        'multipart/form-data',
      ],
    });

    new route53.ARecord(this, 'ApiAliasRecord', {
      zone: hostedZone,
      recordName: `api.sandbox.jurisai.uk`,
      target: route53.RecordTarget.fromAlias(new targets.ApiGateway(api)),
    });


    // --------------------------------------------------------------
    // ---------------- WEB SOCKET API -----------------------------
    // --------------------------------------------------------------

    // WebSocket API definition
    const websocketApi = new apigatewayv2.CfnApi(this, 'WebSocketAPI', {
      name: `${this.stage}-WebSocketAPI`,
      protocolType: 'WEBSOCKET',
      routeSelectionExpression: '$request.body.action',
    });

    // WebSocket $connect Lambda
    const connectLambda = new lambda.Function(this, 'WebSocketConnectLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.X86_64,
      handler: 'websocket_connect.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'websocket_connect', 'websocket_connect.zip')),
      memorySize: 128,
      timeout: cdk.Duration.seconds(10),
      layers: [dependenciesLayer, sharedLayer],
    });

    // WebSocket $disconnect Lambda
    const disconnectLambda = new lambda.Function(this, 'WebSocketDisconnectLambda', {
      runtime: lambda.Runtime.PYTHON_3_11,
      architecture: lambda.Architecture.X86_64,
      handler: 'websocket_disconnect.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '..', '..', 'backend', 'dist', 'websocket_disconnect', 'websocket_disconnect.zip')),
      memorySize: 128,
      timeout: cdk.Duration.seconds(10),
      layers: [dependenciesLayer, sharedLayer],
    });

    // Custom domain for WebSocket API
    const websocketCertificate = new acm.Certificate(this, 'WebSocketApiCertificate', {
      domainName: `socket.api.sandbox.jurisai.uk`,
      validation: acm.CertificateValidation.fromDns(hostedZone),
    });

    const connectIntegration = new apigatewayv2.CfnIntegration(this, 'ConnectIntegration', {
      apiId: websocketApi.ref,
      integrationType: 'AWS_PROXY',
      integrationUri: connectLambda.functionArn,
    });

    const disconnectIntegration = new apigatewayv2.CfnIntegration(this, 'DisconnectIntegration', {
      apiId: websocketApi.ref,
      integrationType: 'AWS_PROXY',
      integrationUri: disconnectLambda.functionArn,
    });

    const connectRoute = new apigatewayv2.CfnRoute(this, 'ConnectRoute', {
      apiId: websocketApi.ref,
      routeKey: '$connect',
      target: `integrations/${connectIntegration.ref}`,
    });

    const disconnectRoute = new apigatewayv2.CfnRoute(this, 'DisconnectRoute', {
      apiId: websocketApi.ref,
      routeKey: '$disconnect',
      target: `integrations/${disconnectIntegration.ref}`,
    });

    // Deployment should occur only after routes are created
    const websocketDeployment = new apigatewayv2.CfnDeployment(this, 'WebSocketAPIDeployment', {
      apiId: websocketApi.ref,
    });

    // Create a dependency between routes and deployment
    websocketDeployment.addDependency(connectRoute);
    websocketDeployment.addDependency(disconnectRoute);

    const websocketDomain = new apigatewayv2.CfnDomainName(this, 'WebSocketCustomDomain', {
      domainName: `socket.api.sandbox.jurisai.uk`,
      domainNameConfigurations: [
        {
          certificateArn: websocketCertificate.certificateArn,
          endpointType: 'REGIONAL',
        },
      ],
    });

    new apigatewayv2.CfnApiMapping(this, 'WebSocketApiMapping', {
      apiId: websocketApi.ref,
      domainName: websocketDomain.ref,
      stage: this.stage,
    });

    // Route53 record for WebSocket subdomain
    new route53.ARecord(this, 'WebSocketAliasRecord', {
      zone: hostedZone,
      recordName: `socket.api.sandbox.jurisai.uk`,
      target: route53.RecordTarget.fromAlias(
        new targets.ApiGatewayv2DomainProperties(
          websocketDomain.attrRegionalDomainName,
          websocketDomain.attrRegionalHostedZoneId,
        ),
      ),
    });

    new apigatewayv2.CfnStage(this, 'WebSocketAPIStage', {
      apiId: websocketApi.ref,
      deploymentId: websocketDeployment.ref,
      stageName: this.stage,
    });

    // Grant permissions to the lambdas
    connectLambda.addPermission('InvokeByApiGateway', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:${websocketApi.ref}/*`,
    });

    disconnectLambda.addPermission('InvokeByApiGateway', {
      principal: new iam.ServicePrincipal('apigateway.amazonaws.com'),
      sourceArn: `arn:aws:execute-api:${cdk.Aws.REGION}:${cdk.Aws.ACCOUNT_ID}:${websocketApi.ref}/*`,
    });

    connectLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: secretsForInfra,
    }));

    disconnectLambda.addToRolePolicy(new iam.PolicyStatement({
      actions: ['secretsmanager:GetSecretValue'],
      resources: secretsForInfra,
    }));
  }

  isProd(): boolean {
    return this.stage == "prod"
  }
}
