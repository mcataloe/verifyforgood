from pathlib import Path


def test_gitlab_ci_defines_backend_runtime_image_build_publish_and_deploy_flow():
    content = Path(".gitlab-ci.yml").read_text(encoding="utf-8")

    assert "stages:" in content
    assert "- validate" in content
    assert "- build-images" in content
    assert "- publish-images" in content
    assert "- terraform-plan" in content
    assert "- terraform-deploy" in content
    assert 'RUNTIME_IMAGE_TAG: "$CI_COMMIT_SHA"' in content

    assert "build_backend_api_image" in content
    assert "build_backend_worker_image" in content
    assert "build_backend_ingest_task_image" in content
    assert 'docker build -f "$RUNTIME_DOCKERFILE" -t "$LOCAL_IMAGE_NAME:$RUNTIME_IMAGE_TAG" .' in content
    assert "backend/customer-api/Dockerfile" in content
    assert "backend/worker/Dockerfile" in content
    assert "backend/ingest/federal/Dockerfile" in content

    assert "publish_runtime_images_dev" in content
    assert "publish_runtime_images_prod" in content
    assert 'terraform -chdir=infrastructure output -raw api_ecr_repository_url' in content
    assert 'terraform -chdir=infrastructure output -raw worker_ecr_repository_url' in content
    assert 'terraform -chdir=infrastructure output -raw monthly_ingest_worker_ecr_repository_url' in content
    assert 'docker push "$API_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"' in content
    assert 'docker push "$WORKER_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"' in content
    assert 'docker push "$INGEST_TASK_ECR_REPOSITORY_URL:$RUNTIME_IMAGE_TAG"' in content
    assert 'aws ecr get-login-password --region "$AWS_REGION"' in content

    assert "terraform_plan_dev" in content
    assert "terraform_apply_dev" in content
    assert "terraform_plan_prod" in content
    assert "terraform_apply_prod" in content
    assert 'backend-config=backend-dev.hcl' in content
    assert 'backend-config=backend-prod.hcl' in content
    assert '-var "api_ecs_image_tag=$RUNTIME_IMAGE_TAG"' in content
    assert '-var "worker_ecs_image_tag=$RUNTIME_IMAGE_TAG"' in content
    assert '-var "monthly_ingest_worker_image_tag=$RUNTIME_IMAGE_TAG"' in content
    assert "when: manual" in content
    assert "TERRAFORM_DEV_SECRETS_TFVARS" in content
    assert "TERRAFORM_PROD_SECRETS_TFVARS" in content


def test_docs_describe_gitlab_pipeline_commit_sha_rollout_and_ingest_compatibility():
    readme = Path("README.md").read_text(encoding="utf-8")
    infra_readme = Path("infrastructure/README.md").read_text(encoding="utf-8")
    backend_readme = Path("backend/README.md").read_text(encoding="utf-8")

    assert "`.gitlab-ci.yml` is now the canonical GitLab CI/CD pipeline" in readme
    assert "immutable commit-SHA tags" in readme
    assert "`monthly_ingest_worker_image_tag` still selects the `backend/ingest/federal`" in readme
    assert "`TERRAFORM_DEV_SECRETS_TFVARS`" in readme
    assert "`TERRAFORM_PROD_SECRETS_TFVARS`" in readme

    assert "GitLab CI/CD rollout baseline" in infra_readme
    assert "`api_ecs_image_tag=$CI_COMMIT_SHA`" in infra_readme
    assert "`worker_ecs_image_tag=$CI_COMMIT_SHA`" in infra_readme
    assert "`monthly_ingest_worker_image_tag=$CI_COMMIT_SHA`" in infra_readme
    assert "managed ECR repositories must exist in Terraform state" in infra_readme
    assert "CI publish" in infra_readme

    assert "GitLab CI now builds all three backend runtime images" in backend_readme


def test_example_tfvars_stop_recommending_latest_image_tags_and_include_worker_controls():
    shared_example = Path("infrastructure/terraform.shared.tfvars.example").read_text(encoding="utf-8")
    root_example = Path("infrastructure/terraform.tfvars.example").read_text(encoding="utf-8")
    dev_example = Path("infrastructure/terraform-dev.tfvars.example").read_text(encoding="utf-8")
    prod_example = Path("infrastructure/terraform-prod.tfvars.example").read_text(encoding="utf-8")

    assert 'api_ecs_image_tag                        = "set-by-ci-commit-sha"' in shared_example
    assert 'worker_ecs_image_tag                     = "set-by-ci-commit-sha"' in shared_example
    assert 'monthly_ingest_worker_image_tag          = "set-by-ci-commit-sha"' in shared_example
    assert 'api_ecs_image_tag = "set-by-ci-commit-sha"' in root_example
    assert 'worker_ecs_image_tag = "set-by-ci-commit-sha"' in root_example
    assert 'monthly_ingest_worker_image_tag = "set-by-ci-commit-sha"' in root_example
    assert "worker_ecs_enabled" in shared_example
    assert "worker_ecs_secret_arns" in shared_example
    assert "worker_ecs_vpc_id" in dev_example
    assert "worker_ecs_private_subnet_ids" in dev_example
    assert "worker_ecs_image_uri" in dev_example
    assert "worker_ecs_vpc_id" in prod_example
    assert "worker_ecs_private_subnet_ids" in prod_example
    assert "worker_ecs_image_uri" in prod_example


def test_managed_ecr_outputs_remain_available_for_ci_even_before_runtime_enablement():
    api_ecs = Path("infrastructure/aws_api_ecs.tf").read_text(encoding="utf-8")
    ecs = Path("infrastructure/aws_ecs.tf").read_text(encoding="utf-8")
    outputs = Path("infrastructure/outputs.tf").read_text(encoding="utf-8")

    assert 'api_ecs_managed_image_enabled = trim(var.api_ecs_image_uri, " ") == ""' in api_ecs
    assert 'count = local.api_ecs_managed_image_enabled ? 1 : 0' in api_ecs
    assert 'worker_ecs_managed_image_enabled = trim(var.worker_ecs_image_uri, " ") == ""' in ecs
    assert 'monthly_ingest_managed_image_enabled = trim(var.monthly_ingest_worker_image_uri, " ") == ""' in ecs
    assert 'count = local.monthly_ingest_managed_image_enabled ? 1 : 0' in ecs
    assert 'value       = local.api_ecs_managed_image_enabled ? aws_ecr_repository.api[0].repository_url : null' in outputs
    assert 'value       = local.worker_ecs_managed_image_enabled ? aws_ecr_repository.worker[0].repository_url : null' in outputs
    assert 'value       = local.monthly_ingest_managed_image_enabled ? aws_ecr_repository.monthly_ingest_worker[0].repository_url : null' in outputs
