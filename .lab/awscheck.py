#!/usr/bin/env python3
import json, os, re, subprocess, sys, time, urllib.request
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
os.chdir(ROOT)
passed = failed = 0


def check(desc, ok, hint=""):
    global passed, failed
    if ok:
        passed += 1; print("PASS  " + desc)
    else:
        failed += 1; print("FAIL  " + desc + (("   -> " + hint) if hint else ""))


def aws(*a):
    try:
        return json.loads(subprocess.check_output(("aws",) + a + ("--output", "json"), stderr=subprocess.DEVNULL, timeout=60) or "null")
    except Exception:
        return None


check("no AWS keys in the repository", subprocess.run("git grep -lE 'AKIA[0-9A-Z]{16}' -- . ':!.lab' ':!verify.sh'", shell=True, capture_output=True, text=True).stdout.strip() == "")
print("== The load balancer ==")
lbs = [l for l in (aws("elbv2", "describe-load-balancers") or {}).get("LoadBalancers", []) if l["LoadBalancerName"] == "clippy-alb"]
check("an Application Load Balancer named clippy-alb exists, internet-facing and active", len(lbs) == 1 and lbs[0]["Type"] == "application" and lbs[0]["Scheme"] == "internet-facing" and lbs[0]["State"]["Code"] == "active", "./... see Part 3")
lb = lbs[0] if lbs else {}
check("it spans at least 2 availability zones", len(lb.get("AvailabilityZones", [])) >= 2)
tgs = [t for t in (aws("elbv2", "describe-target-groups") or {}).get("TargetGroups", []) if t["TargetGroupName"] == "clippy-web"]
tg = tgs[0] if tgs else {}
check("target group clippy-web: HTTP port 80, health check on /healthz", bool(tg) and tg["Port"] == 80 and tg["Protocol"] == "HTTP" and tg["HealthCheckPath"] == "/healthz")
check("health check is fast: interval 30s or less, unhealthy threshold 3 or less", bool(tg) and tg["HealthCheckIntervalSeconds"] <= 30 and tg["UnhealthyThresholdCount"] <= 3)
lis = (aws("elbv2", "describe-listeners", "--load-balancer-arn", lb["LoadBalancerArn"]) or {}).get("Listeners", []) if lb else []
check("a listener on port 80 forwards to the target group", any(l["Port"] == 80 and any(a.get("TargetGroupArn") == tg.get("TargetGroupArn") for a in l["DefaultActions"]) for l in lis))

print("== The Auto Scaling group ==")
g = ((aws("autoscaling", "describe-auto-scaling-groups", "--auto-scaling-group-names", "clippy-web") or {}).get("AutoScalingGroups") or [None])[0]
check("an Auto Scaling group clippy-web exists", bool(g))
if not g:
    print("\nNothing else can be checked.\n%d check(s) failed, %d passed" % (failed, passed)); sys.exit(1)
check("minimum 2, maximum 4 (and desired between them)", g["MinSize"] == 2 and g["MaxSize"] == 4 and 2 <= g["DesiredCapacity"] <= 4)
check("health check type is ELB (a server that fails /healthz is replaced, not just one that is powered off)", g["HealthCheckType"] == "ELB")
check("it is attached to the target group", tg.get("TargetGroupArn") in g.get("TargetGroupARNs", []))
check("its servers are spread over at least 2 availability zones", len({i["AvailabilityZone"] for i in g["Instances"]}) >= 2, "found %s" % sorted({i["AvailabilityZone"] for i in g["Instances"]}))
pol = (aws("autoscaling", "describe-policies", "--auto-scaling-group-name", "clippy-web") or {}).get("ScalingPolicies", [])
check("a target tracking policy on average CPU (target between 30 and 70)", any(p["PolicyType"] == "TargetTrackingScaling" and "CPU" in p["TargetTrackingConfiguration"]["PredefinedMetricSpecification"]["PredefinedMetricType"] and 30 <= p["TargetTrackingConfiguration"]["TargetValue"] <= 70 for p in pol))
ids = [i["InstanceId"] for i in g["Instances"]]
insts = [i for r in (aws("ec2", "describe-instances", "--instance-ids", *ids) or {}).get("Reservations", []) for i in r["Instances"]] if ids else []
check("servers are tagged lab=aws-alb-asg and require IMDSv2", bool(insts) and all(any(t["Key"] == "lab" and t["Value"] == "aws-alb-asg" for t in i.get("Tags", [])) and i["MetadataOptions"]["HttpTokens"] == "required" for i in insts))

print("== The security groups ==")
def rules(gid):
    return [r for r in (aws("ec2", "describe-security-group-rules", "--filters", "Name=group-id,Values=" + gid) or {}).get("SecurityGroupRules", []) if not r["IsEgress"]]
alb_sg = lb.get("SecurityGroups", [None])[0] if lb else None
web_sgs = {s["GroupId"] for i in insts for s in i.get("SecurityGroups", [])}
ar = rules(alb_sg) if alb_sg else []
check("the load balancer accepts port 80 from anywhere and nothing else", len(ar) == 1 and ar[0]["FromPort"] == 80 and ar[0].get("CidrIpv4") == "0.0.0.0/0")
wr = [r for gid in web_sgs for r in rules(gid)]
check("the servers accept port 80 ONLY from the load balancer's security group (not from the internet, not by CIDR)",
      len(wr) == 1 and wr[0]["FromPort"] == 80 and wr[0].get("ReferencedGroupInfo", {}).get("GroupId") == alb_sg)

print("== Use it ==")
dns = lb.get("DNSName")
th = (aws("elbv2", "describe-target-health", "--target-group-arn", tg.get("TargetGroupArn")) or {}).get("TargetHealthDescriptions", []) if tg else []
healthy = [t for t in th if t["TargetHealth"]["State"] == "healthy"]
check("at least 2 targets are healthy", len(healthy) >= 2, "states: %s" % [t["TargetHealth"]["State"] for t in th])
seen = set(); codes = []
for _ in range(20):
    try:
        with urllib.request.urlopen("http://%s/healthz" % dns, timeout=8) as r:
            codes.append(r.status); seen.add(json.loads(r.read().decode()).get("version"))
    except Exception:
        codes.append(0)
check("20 requests to the load balancer all answer 200", codes.count(200) == 20, "%s" % codes)
check("the answers come from at least 2 different servers (the version field shows the instance id)", len(seen) >= 2, "seen: %s" % sorted(map(str, seen)))
act = (aws("autoscaling", "describe-scaling-activities", "--auto-scaling-group-name", "clippy-web", "--max-items", "50") or {}).get("Activities", [])
term = [a for a in act if a["Description"].startswith("Terminating EC2 instance")]
launched_after = term and any(a["Description"].startswith("Launching a new EC2 instance") and a["StartTime"] > min(t["StartTime"] for t in term) for a in act)
check("the activity history shows a server terminated and a replacement launched (you killed one on purpose)", bool(launched_after), "terminate one server and wait")
print()
print(("ALL CHECKS PASSED (%d/%d)" % (passed, passed)) if failed == 0 else ("%d check(s) failed, %d passed" % (failed, passed)))
sys.exit(1 if failed else 0)
