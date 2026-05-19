# Service code index

The SPA uses internal `serviceCode` strings that don't always match the public service name. This is the index from common references → SPA `serviceCode` → module file. Read the linked module before building any line item for that service.

## Currently supported

All modules below have been verified end-to-end: the formulas reproduce the captured `serviceCost.monthly` from a real saveAs body within rounding tolerance (most within $0.05, all within $1).

### Compute & databases

| User says | SPA serviceCode | Module |
|---|---|---|
| EC2, Linux/Windows VM, instance | `ec2Enhancement` | [`service-modules/ec2.md`](service-modules/ec2.md) |
| RDS PostgreSQL, Postgres database | `amazonRDSPostgreSQLDB` | [`service-modules/rds-postgres.md`](service-modules/rds-postgres.md) |
| RDS SQL Server, MS SQL on RDS | `amazonRDSForSQLServer` (note: `estimateFor` is the literal string `"rdsForOracle"` — SPA reuses the Oracle form) | [`service-modules/rds-sqlserver.md`](service-modules/rds-sqlserver.md) |
| Fargate, ECS tasks, serverless containers, EKS pods on Fargate — **Linux x86 On-Demand only**; Linux ARM, Windows, Fargate Spot, and ephemeral storage > 20 GB/task are NOT yet round-tripped (Pricing API rates documented for ARM/Windows; capture HAR before quoting them or Spot) | `awsFargate` (`estimateFor: template`) | [`service-modules/fargate.md`](service-modules/fargate.md) |
| EKS, Elastic Kubernetes Service, K8s control plane, EKS Hybrid Nodes, ArgoCD/ACK/KRO platform capabilities — covers control plane (Standard + Extended Support), Hybrid Nodes (per-vCPU tiered), and the EKS Capabilities add-ons; **EKS Auto Mode NOT captured**, **EC2 worker nodes** must be billed via the `ec2Enhancement` module, **Fargate pods on EKS** via `awsFargate` | `awsEks` (`estimateFor` is the literal `"Amazon EKS"` — with a space, not a form-id slug) | [`service-modules/eks.md`](service-modules/eks.md) |

### Storage & networking

| User says | SPA serviceCode | Module |
|---|---|---|
| S3, S3 storage, S3 with data transfer | `amazonSimpleStorageServiceGroup` (group with `amazonS3Standard`, `awsS3DataTransfer`, etc. as sub-services) | [`service-modules/s3.md`](service-modules/s3.md) |
| VPC, Site-to-Site VPN, Transit Gateway | `amazonVirtualPrivateCloud` (group with `vpnConnectionVpc`, `transitGatewayVpc`, etc. as sub-services) | [`service-modules/vpc.md`](service-modules/vpc.md) |
| ELB, ALB, NLB, GWLB, Application/Network/Gateway Load Balancer (Classic LB NOT covered) — ALB LCU formula is the SPA's empirical bytes-additive variant, not AWS's documented max-across; tight quotes need a second capture | `elasticLoadBalancing` (group with `applicationLoadBalancer`, `networkLoadBalancer`, `gatewayLoadBalancer` sub-services) | [`service-modules/elb.md`](service-modules/elb.md) |
| CloudFront — **Flat-Rate Plans only** (Free / Pro / Business / Premium subscription tiers); usage-based per-GB / per-request CDN pricing is NOT yet supported — capture HAR and add module before quoting metered CDN traffic | `amazonCloudFront` (`estimateFor: productPackd1`) | [`service-modules/cloudfront.md`](service-modules/cloudfront.md) |
| FSx for Windows File Server — **`singleAZDeployment` only**; Multi-AZ Windows, Lustre, ONTAP, OpenZFS are NOT covered — capture and add a module before quoting them | `amazonFSx` (`estimateFor: singleAZDeployment`) | [`service-modules/fsx-windows.md`](service-modules/fsx-windows.md) |
| ECR, Elastic Container Registry, image registry, container image storage — storage + outbound DT only; replication / Enhanced scanning / pull-through cache are NOT modeled | `amazonElasticContainerRegistry` (`estimateFor: template_0`) | [`service-modules/ecr.md`](service-modules/ecr.md) |
| AWS Transfer Family — **Web Apps sub-service only**; SFTP/FTPS/FTP server endpoints and AS2/SFTP connectors are NOT yet captured. Don't quote anything but Web Apps without first capturing a HAR | `aWSTransferForSFTP` (lowercase `a`, uppercase `WS`; group with `webApps` sub-service) | [`service-modules/transfer-family.md`](service-modules/transfer-family.md) |
| AWS Managed Microsoft AD, Directory Service, Active Directory — **AWS Managed Microsoft AD only**; AD Connector and Simple AD have different `estimateFor` values and are NOT covered. Unusual shape: `columnFormIPM_*` arrays of row objects with human-readable string keys (`"Directory Size"`, `"Number Of Addl Domain Controllers"`, etc.) | `aWSDirectoryService` (lowercase `a`, uppercase `WS`; `estimateFor: managedMicrosoftActiveDirectory`) | [`service-modules/directory-service.md`](service-modules/directory-service.md) |
| Direct Connect, DX, dedicated network, private connection to AWS — **Dedicated ports captured**; hosted/sub-1G ports have the same shape but rates not yet verified. `region` field is decorative; pricing follows the `port:Direct Connect Location` colocation site | `awsDirectConnect` (`estimateFor: template`, flat shape with `columnFormIPM` row-objects + top-level `dataTransferOut` / `datatransferin` / `utilization`) | [`service-modules/direct-connect.md`](service-modules/direct-connect.md) |

### Security & governance

| User says | SPA serviceCode | Module |
|---|---|---|
| Secrets Manager, secret storage | `awsSecretsManager` | [`service-modules/secrets-manager.md`](service-modules/secrets-manager.md) |
| Security Hub, compliance checks | `awsSecurityHub` | [`service-modules/security-hub.md`](service-modules/security-hub.md) |
| AWS Config, config items, conformance pack | `awsConfig` | [`service-modules/aws-config.md`](service-modules/aws-config.md) |
| CloudTrail, audit logs, CloudTrail Lake | `awsCloudTrail` | [`service-modules/cloudtrail.md`](service-modules/cloudtrail.md) |
| WAF, web ACL, web application firewall | `awsWebApplicationFirewall` | [`service-modules/waf.md`](service-modules/waf.md) |
| GuardDuty, threat detection | `amazonGuardDuty` | [`service-modules/guardduty.md`](service-modules/guardduty.md) |
| Inspector, vulnerability scanning, SAST/SCA/IaC | `amazonInspector` (v2) | [`service-modules/inspector.md`](service-modules/inspector.md) |
| Systems Manager, SSM, Parameter Store, SSM Automation, Just-in-Time node access — **only those three sub-services covered**; Patch Manager / Run Command / OpsCenter / Change Manager / Incident Manager need a HAR before quoting. Parameter Store and Automation formulas are best-effort pending a second capture | `awsSystemsManager` (group with `awsSystemsManagerParameterStore`, `awsSystemsManagerAutomation`, `justInTimeNodeAccess` sub-services) | [`service-modules/systems-manager.md`](service-modules/systems-manager.md) |
| Shield, Shield Advanced, DDoS protection — **Shield Advanced only** (Standard is free, no line item); base $3,000/month subscription IS included in serviceCost; org-level subscription handling is NOT modeled — ask if user is in an AWS Organization | `awsShield` (`estimateFor: template`, flat shape; cc has top-level `cloudFrontUsage`, `LoadBalancingUsage` (PascalCase outlier), `elasticIpUsage`, `globalAcceleratorUsage` in tb\|month) | [`service-modules/shield.md`](service-modules/shield.md) |

### Streaming, messaging & queues

| User says | SPA serviceCode | Module |
|---|---|---|
| Kinesis Data Streams (Provisioned / OnDemand / OnDemand Advantage) | `amazonKinesisDataStreams` — `estimateFor` selects the mode | [`service-modules/kinesis-data-streams.md`](service-modules/kinesis-data-streams.md) |
| Data Firehose, Kinesis Firehose | `amazonKinesisFirehose` | [`service-modules/kinesis-firehose.md`](service-modules/kinesis-firehose.md) |
| SNS, topic, notification | `amazonSimpleNotificationService` (group with `standardTopics` + `fifoTopics` sub-services) | [`service-modules/sns.md`](service-modules/sns.md) |
| SQS, queue | `amazonSimpleQueueService` | [`service-modules/sqs.md`](service-modules/sqs.md) |

### Developer tools & CI/CD

| User says | SPA serviceCode | Module |
|---|---|---|
| CodeDeploy, on-prem deployments, hybrid CI/CD | `awsCodeDeploy` (on-prem path only; EC2/Lambda/ECS deployments are free) | [`service-modules/codedeploy.md`](service-modules/codedeploy.md) |
| CodePipeline, V1 active pipelines, V2 action-execution minutes | `awsCodePipeline` (combined V1 + V2 form; first V1 pipeline/account/month is free) | [`service-modules/codepipeline.md`](service-modules/codepipeline.md) |
| CodeBuild, managed build runners, CI build minutes | `awsCodeBuild` (**On-Demand EC2 fleet only**; Lambda / Windows / Reserved / GPU / macOS fleets are NOT yet captured — capture HAR and extend module before quoting them) | [`service-modules/codebuild.md`](service-modules/codebuild.md) |

## Not yet supported

The AWS Pricing Calculator covers 436 services. Coverage in this skill grows as modules are written. If the user's brief references a service not in the table above, follow the rule in `SKILL.md` (Step 1 / "When the user's brief covers a service you don't have a module for"): name the unsupported items, propose to skip or add a module, and let the user decide.

To add a new module, see `service-modules/_template.md` and the workflow in `SKILL.md`.
