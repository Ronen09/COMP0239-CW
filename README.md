## Running the Pipeline Commands

*Execute commands from the root directory of the project.*

1.  **Provision Infrastructure:**
    ```bash
    cd terraform/
    terraform init
    terraform apply -auto-approve # Uses defaults from variables.tf
    cd ..
    ```

2.  **Configure Nodes & Start Services:**
    ```bash
    # Use correct private key path if not default
    ansible-playbook ansible/site.yaml -i generate_inventory.py --private-key ~/.ssh/id_ed25519
    ```
    *(Wait for completion)*

3.  **Run the Spark Analysis Job:**
    ```bash
    # Use correct private key path if not default
    # Ensure run_spark_swe_llama.py is in ansible/
    # Ensure MinIO keys are set securely in run-analysis.yaml
    ansible-playbook ansible/run-analysis.yaml -i generate_inventory.py --private-key ~/.ssh/id_ed25519
    ```
    *(This runs asynchronously; monitor Spark/MinIO UIs)*

## Accessing Outputs & Monitoring

*   **Results (MinIO):**
    *   Check the MinIO bucket specified (default `analysis-results`).
    *   Access via S3 endpoint for clients (`mc`, Spark S3A connector): `http://ucabroy-minio-s3.condenser.ucl.ac.uk`.
    *   Access the MinIO Web UI (Console): Find the ingress hostname (often uses port 9001 internally, e.g., `http://ucabroy-minio-console.condenser.ucl.ac.uk` - check ingress setup) and log in with Username: `guiuser` / Password: `abcd1234`. 
*   **Grafana:** Access via its ingress hostname: `https://ucabroy-cw-grafana.condenser.ucl.ac.uk`. Default login is often `admin`/`admin`.
*   **Spark UI:**
    *   Master: `http://ucabroy-spark-master-ui.condenser.ucl.ac.uk`.
    *   Application UI (while running): `http://ucabroy-spark-app-ui.condenser.ucl.ac.uk`.
*   **Prometheus:** `https://ucabroy-cw-prometheus.condenser.ucl.ac.uk`.

## Cleaning Up

1.  **Destroy Infrastructure:**
    ```bash
    cd terraform/
    terraform destroy -auto-approve
    cd ..
    ```