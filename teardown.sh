#!/usr/bin/env bash
# Deletes the Auto Scaling group (and its servers), the load balancer, the target group, the launch template and the security groups.
set -u
aws sts get-caller-identity >/dev/null 2>&1 || { echo "No working AWS credentials." >&2; exit 1; }
if aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names clippy-web --query 'AutoScalingGroups[0].AutoScalingGroupName' --output text 2>/dev/null | grep -q clippy-web; then
  echo "Deleting the Auto Scaling group and terminating its servers..."
  aws autoscaling delete-auto-scaling-group --auto-scaling-group-name clippy-web --force-delete
  for _ in $(seq 1 60); do aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names clippy-web --query 'AutoScalingGroups[0]' --output text 2>/dev/null | grep -q None && break; sleep 5; done
fi
for arn in $(aws elbv2 describe-load-balancers --query "LoadBalancers[?LoadBalancerName=='clippy-alb'].LoadBalancerArn" --output text 2>/dev/null); do
  aws elbv2 delete-load-balancer --load-balancer-arn "$arn" && echo "deleting load balancer"
  for _ in $(seq 1 40); do aws elbv2 describe-load-balancers --load-balancer-arns "$arn" >/dev/null 2>&1 || break; sleep 5; done
done
for arn in $(aws elbv2 describe-target-groups --query "TargetGroups[?TargetGroupName=='clippy-web'].TargetGroupArn" --output text 2>/dev/null); do
  for _ in 1 2 3 4 5 6 7 8 9 10; do aws elbv2 delete-target-group --target-group-arn "$arn" >/dev/null 2>&1 && { echo "deleted target group"; break; }; sleep 10; done
done
aws ec2 delete-launch-template --launch-template-name clippy-web >/dev/null 2>&1 && echo "deleted launch template"
# security groups: network interfaces of the load balancer take a minute to disappear
for n in clippy-web clippy-alb; do
  for _ in $(seq 1 30); do
    ids=$(aws ec2 describe-security-groups --filters Name=group-name,Values=$n --query 'SecurityGroups[].GroupId' --output text)
    [ -z "$ids" ] && break
    for g in $ids; do aws ec2 delete-security-group --group-id $g >/dev/null 2>&1 && echo "deleted security group $n"; done
    sleep 6
  done
done
echo "Now run ./verify-teardown.sh"
