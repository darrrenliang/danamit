kubectl create namespace dev

helm repo add minio https://charts.min.io/
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

helm install minio minio/minio \
  --namespace dev \
  -f minio-values.yaml

helm install postgresql bitnami/postgresql \
  --namespace dev \
  -f postgresql-values.yaml