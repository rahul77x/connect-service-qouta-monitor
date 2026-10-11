# Amazon Connect Service Quota Monitor

A simplified, bank-grade operational monitoring and alerting solution for **Amazon Connect Service Quotas**. 

Designed specifically for enterprise and financial services AWS accounts where hosting static web dashboards via S3, CloudFront, Lambda@Edge, or Cognito is restricted by security policies.

---

## 🏛️ Why This Architecture?

| Concern | Reference Sample Repo | Our Bank-Compliant Architecture |
|---|---|---|
| **Dashboard Hosting** | Private S3 + CloudFront + Lambda@Edge + Cognito Hosted UI | **Native Amazon CloudWatch Dashboard** inside AWS Console |
| **Authentication & IAM** | Custom Cognito User Pool & Edge Auth in `us-east-1` | **Existing Corporate SSO & IAM Roles** (AWS IAM Identity Center, Okta, Azure AD) |
| **Data Freshness** | 1-hour batch polling | **1-minute real-time** for active calls, dropped calls, and API rate limits |
| **Alert Latency** | Hourly scan | **Immediate (sub-minute)** CloudWatch Metric Alarms on dropped/throttled calls |
| **Deployment Complexity** | Two-phase Terraform applies + custom JS/HTML builders | **Single-command `terraform apply`** with zero external dependencies |

---

## 📐 Architecture & Data Flow

```mermaid
flowchart TD
    subgraph S1["1. Real-Time Telemetry (1-Minute Resolution)"]
        CONNECT["Amazon Connect"] -->|Emits every 1m| CW_CONNECT["AWS/Connect\n- ConcurrentCalls\n- ThrottledCalls\n- CallsBreachingConcurrencyQuota"]
        USAGE["AWS Internal"] -->|Emits every 1m| CW_USAGE["AWS/Usage\n- CallCount (per Connect API)"]
    end

    subgraph S2["2. Scheduled Quota Collector"]
        EB["EventBridge Rule (rate(15m))"] --> LAMBDA["Quota Monitor Lambda (Python 3.12)"]
        LAMBDA -->|connect:ListInstances| DISCO["Instance Discovery"]
        LAMBDA -->|servicequotas:ListServiceQuotas| SQ["Service Quotas Limits"]
        LAMBDA -->|Connect Listing APIs| APIS["Queues, Numbers, Flows, Profiles"]
        LAMBDA -->|cloudwatch:PutMetricData| CW_CUSTOM["AmazonConnect/ServiceQuotas\n- QuotaUtilizationPercent\n- QuotaUsage\n- QuotaLimit"]
        LAMBDA -->|Usage >= 80%| SNS["Amazon SNS Topic\n(Consolidated Alert)"]
    end

    subgraph S3["3. Alarms & Operations Visualization"]
        CW_CONNECT --> ALARMS["CloudWatch Metric Alarms\n- CallsBreachingQuota > 0\n- ThrottledCalls > 0"]
        CW_CUSTOM --> ALARMS
        ALARMS --> SNS
        CW_CONNECT --> DASH["Amazon CloudWatch Custom Dashboard\n(Gauges, Line Charts, TPS, Bar Charts)"]
        CW_USAGE --> DASH
        CW_CUSTOM --> DASH
        OPERATOR["NOC / Contact Center Ops"] -->|Bank Corporate SSO| DASH
    end
```

---

## 📊 Monitored Quotas & Measurement Methods

| Quota Code | Quota Name | Measurement Method | Data Source |
|---|---|---|---|
| `L-AA17A6B9` | Amazon Connect instance count | `api_count` | `connect:ListInstances` |
| `L-28B936FD` | Active concurrent voice calls | `cloudwatch` (1-min) | `AWS/Connect:ConcurrentCalls` |
| `L-E573B7E9` | Active concurrent chats | `cloudwatch` (1-min) | `AWS/Connect:ActiveChats` |
| `L-515FE427` | Active concurrent tasks | `cloudwatch` (1-min) | `AWS/Connect:ConcurrentTasks` |
| `L-89FE583B` | Phone numbers per instance | `api_count` | `connect:ListPhoneNumbersV2` |
| `L-B67B713A` | Contact flows per instance | `api_count` | `connect:ListContactFlows` |
| `L-0304675A` | Queues per instance | `api_count` | `connect:ListQueues` |
| `L-7CAAC8DF` | Routing profiles per instance | `api_count` | `connect:ListRoutingProfiles` |
| `L-47EE3561` | Hours of operation per instance | `api_count` | `connect:ListHoursOfOperations` |
| `L-D269D71F` | `GetContactAttributes` API rate | `cloudwatch_api` (TPS) | `AWS/Usage:CallCount / 60` |
| `L-FB0E0AC8` | `UpdateContactAttributes` API rate | `cloudwatch_api` (TPS) | `AWS/Usage:CallCount / 60` |
| `L-44670DDF` | `StartOutboundVoiceContact` API rate | `cloudwatch_api` (TPS) | `AWS/Usage:CallCount / 60` |
| `L-C4C4FECE` | `DescribeContact` API rate | `cloudwatch_api` (TPS) | `AWS/Usage:CallCount / 60` |

---

## 🖥️ CloudWatch Dashboard Layout

The dashboard is generated automatically by Terraform and contains:

1. **Header & Status Banner:** Operational instructions, region, and warning thresholds.
2. **Alarm Status Tiles:** Live status widgets for critical telephony breaches, API throttling, and high quota utilization.
3. **Speedometer Gauge Dial:** Displays highest current quota utilization percentage with color-coded safety, warning (80%), and breach (100%) zones.
4. **Active Concurrent Calls (1-Minute Line Chart):** Real-time voice concurrency curve plotted against dynamic warning and hard limit threshold annotations.
5. **API Rate Limits (TPS):** Converts 1-minute `CallCount` into live Transactions Per Second (TPS) across high-volume Connect APIs using CloudWatch Metric Math.
6. **Resource Capacity Bar Chart:** Visualizes allocations for Phone Numbers, Contact Flows, Queues, and Routing Profiles against ceilings.
7. **Comprehensive Quota Headroom Table:** Tabular summary of all monitored items, current counts, and quota ceilings.

---

## 📁 Repository Structure

```text
connect-service-qouta-monitor/
├── src/
│   ├── discovery.py             # Discovers Connect instances & active Service Quotas
│   ├── collector.py             # Collects API counts, CloudWatch metrics, & API TPS
│   ├── publisher.py             # Pushes custom CloudWatch metrics & consolidated alerts
│   ├── lambda_function.py       # Main Lambda handler entrypoint
│   └── quota_definitions.json   # Base catalog of Amazon Connect quotas
├── terraform/
│   ├── versions.tf              # Required Terraform & provider versions
│   ├── providers.tf             # AWS provider configuration
│   ├── variables.tf             # Input variables & validation rules
│   ├── sns.tf                   # Encrypted SNS topic for alerts
│   ├── iam.tf                   # Least-privilege IAM execution role
│   ├── lambda.tf                # Lambda packaging, logs, and function configuration
│   ├── events.tf                # EventBridge scheduled trigger
│   ├── alarms.tf                # Real-time CloudWatch Metric Alarms
│   ├── cloudwatch_dashboard.tf  # Native CloudWatch Dashboard definition
│   ├── outputs.tf               # Resource ARNs and direct console dashboard link
│   └── terraform.tfvars.example # Example variable values
├── tests/                       # Unit test suite (python unittest / pytest)
│   ├── test_discovery.py
│   ├── test_collector.py
│   ├── test_publisher.py
│   └── test_lambda_function.py
├── requirements.txt             # Runtime Python dependencies
├── requirements-dev.txt         # Development & testing dependencies
├── .gitignore
└── README.md
```

---

## 🚀 Deployment Guide

### Prerequisites
- AWS CLI configured with appropriate credentials: `aws sts get-caller-identity`
- Terraform `>= 1.5.0`
- Python `>= 3.10`

### Step 1: Clone and Configure

```bash
cd connect-service-qouta-monitor/terraform

# Create your custom tfvars file
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
aws_region           = "us-east-1"
environment          = "prod"
threshold_percentage = 80
schedule_expression  = "rate(15 minutes)"

# Leave empty to auto-discover all instances, or specify a specific instance ID:
connect_instance_id  = ""
```

### Step 2: Initialize & Deploy

```bash
terraform init
terraform plan
terraform apply
```

Upon completion, Terraform will output:
- `cloudwatch_dashboard_url`: Direct link to open the dashboard in the AWS Console.
- `sns_topic_arn`: ARN of the created notification topic.
- `lambda_function_arn`: ARN of the monitor Lambda.

### Step 3: Configure SNS Subscriptions (Console)

The Terraform configuration creates a managed, encrypted SNS topic (`connect-quota-monitor-<env>-alerts`). 

To subscribe your team:
1. Open the **Amazon SNS Console** in your AWS account.
2. Under **Topics**, click `connect-quota-monitor-prod-alerts`.
3. Click **Create subscription**.
4. Choose your protocol (e.g., **Email**, **SMS**, or **HTTPS** for Slack/MS Teams webhook).
5. Enter the target endpoint and click **Create subscription**.
6. *(For Email)* Confirm the subscription via the verification email sent by AWS.

---

## 🧪 Running Unit Tests Locally

The test suite runs using Python's standard `unittest` runner without requiring AWS credentials:

```bash
python -m unittest discover tests
```

Expected output:
```text
Ran 8 tests in 0.009s
OK
```

---

## 🔒 Security & Banking Compliance
- **Zero Web Perimeter:** No S3 buckets configured for website hosting, no CloudFront distributions, no public API endpoints.
- **Data Protection:** SNS topic encrypted at rest with AWS KMS (`alias/aws/sns`).
- **Least Privilege:** IAM policies explicitly scope permissions to read-only Connect and Service Quota operations.
- **Role-Based Access Control:** Dashboard access is protected by native AWS Console IAM / Corporate SSO identity federation.

