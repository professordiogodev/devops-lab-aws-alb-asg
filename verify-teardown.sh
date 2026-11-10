#!/usr/bin/env bash
# Proves the lab left nothing in AWS. Run with: ./verify-teardown.sh
set -u
ACCOUNT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || { echo "No working AWS credentials." >&2; exit 1; }
echo "Checking account $ACCOUNT, region $(aws configure get region)"
pass=0; failn=0
check() { local d="$1"; shift; if "$@" >/dev/null 2>&1; then echo "PASS  $d"; pass=$((pass+1)); else echo "FAIL  $d"; failn=$((failn+1)); fi; }
empty() { local r; r=$(eval "$1" 2>/dev/null); [ -z "$r" ] || [ "$r" = None ]; }
check "no Auto Scaling group clippy-web" empty "aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names clippy-web --query 'AutoScalingGroups[].AutoScalingGroupName' --output text"
check "no load balancer clippy-alb (it bills every hour)" empty "aws elbv2 describe-load-balancers --query \"LoadBalancers[?LoadBalancerName=='clippy-alb'].LoadBalancerArn\" --output text"
check "no target group clippy-web" empty "aws elbv2 describe-target-groups --query \"TargetGroups[?TargetGroupName=='clippy-web'].TargetGroupArn\" --output text"
check "no launch template clippy-web" bash -c "! aws ec2 describe-launch-templates --launch-template-names clippy-web >/dev/null 2>&1"
check "no running server tagged lab=aws-alb-asg" empty "aws ec2 describe-instances --filters Name=tag:lab,Values=aws-alb-asg Name=instance-state-name,Values=pending,running,stopping,stopped --query 'Reservations[].Instances[].InstanceId' --output text"
check "no security groups clippy-alb or clippy-web" empty "aws ec2 describe-security-groups --filters Name=group-name,Values=clippy-alb,clippy-web --query 'SecurityGroups[].GroupId' --output text"
echo
if [ "$failn" -eq 0 ]; then echo "TEARDOWN VERIFIED ($pass/$pass) in account $ACCOUNT"; else echo "NOT CLEAN: $failn leftover(s). Remove them and run this again."; fi
exit "$failn"
