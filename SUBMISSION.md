# Submission

Fork URL: <!-- paste the URL of your fork here -->

## Files to commit

- [ ] `notes.md` with your commands and what you saw (optional)

## Questions

Answer in your own words. Where a question asks for output, paste it in a code block.

### Q1. Paste the target group health check settings and the state of the targets (`aws elbv2 describe-target-health`). Why does the health check use `/healthz` and not `/`?

**Your answer:**

<!-- replace this line with your answer -->

### Q2. Terminate one server on purpose and paste the Auto Scaling activity history and a loop of `curl` against the load balancer during the replacement. Did any request fail? What decides how many?

**Your answer:**

<!-- replace this line with your answer -->

### Q3. Show the security groups: why does the instance group allow port 80 from the load balancer's group and not from the world?

**Your answer:**

<!-- replace this line with your answer -->

### Q4. Paste the target tracking policy. What happens to the number of servers when CPU goes above the target for a few minutes, and what stops it growing forever?

**Your answer:**

<!-- replace this line with your answer -->

### Q5. What is the difference between the load balancer health check and the Auto Scaling health check type (`EC2` or `ELB`)? Which did you choose and why?

**Your answer:**

<!-- replace this line with your answer -->

### Q6. Paste the output of `./verify.sh`. It must end with **ALL CHECKS PASSED**.

**Your answer:**

<!-- replace this line with your answer -->

### Q7. **Tear down.** Paste the output of `./verify-teardown.sh`. It must end with **TEARDOWN VERIFIED**.

**Your answer:**

<!-- replace this line with your answer -->
