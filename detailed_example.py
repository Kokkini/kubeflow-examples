from multiprocessing import shared_memory
import kfp.dsl as dsl
import kfp
from kubernetes import client as k8s_client


@dsl.pipeline(
    name='goose-pipeline',
    description='detailed kubeflow example'
)
def pipeline(
    num_gpu="1",
    gpu_type='NVIDIA-RTX-A6000',
    minio_bucket_name="goose-bucket",
    minio_file="dataset.zip"
):
    # training container
    training = dsl.ContainerOp(
        name="training",
        image="yourAwesomeImage:v6.6.6",
        command=["python", "train.py"]
    )

    # add GPU, CPU and RAM resources
    training.container.add_resource_limit('nvidia.com/gpu', num_gpu)
    training.container.add_resource_request('cpu', "1000m")
    training.container.add_resource_request('memory', "4Gi")

    # add node selector so it can chooses the GPU
    training.add_node_selector_constraint(
        'nvidia.com/gpu.product', gpu_type)

    # add ENV variables
    training_env_var = {
        "PYTHONPATH": ".",
        "MINIO_SITE_URL": "https://minio.your.domain",
        "MINIO_BUCKET_NAME": minio_bucket_name,
        "MINIO_FILE": minio_file
    }
    for key, value in training_env_var.items():
        training.container.add_env_variable(
            k8s_client.V1EnvVar(name=key, value=value))

    # add existing k8s secrets
    k8s_secret_name = "minio-cred"
    keys_in_secrets = ["MINIO_ACCESS_KEY", "MINIO_SECRET_KEY"]
    for key in keys_in_secrets:
        training.container.add_env_variable(
            k8s_client.V1EnvVar(
                name=key,
                value_from=k8s_client.V1EnvVarSource(
                    secret_key_ref=k8s_client.V1SecretKeySelector(
                        name=k8s_secret_name,
                        key=key
                    )
                )
            )
        )

    # add temporary data volume (emptyDir volume in k8s)
    # data in this volume will be deleted after the pod is terminated
    training.add_volume(k8s_client.V1Volume(
        name='dataset', empty_dir=k8s_client.V1EmptyDirVolumeSource(size_limit='100Gi')))
    training.container.add_volume_mount(k8s_client.V1VolumeMount(
        mount_path='/dataset', name='dataset'))

    # add existing volume
    training.add_pvolumes(pvolumes={
        "/common-logs": dsl.PipelineVolume(pvc="common-logs-pvc")
    })

    # add shared memory
    training.add_volume(k8s_client.V1Volume(
        name='shared-memory', empty_dir=k8s_client.V1EmptyDirVolumeSource(medium="Memory", size_limit=None)))
    training.container.add_volume_mount(k8s_client.V1VolumeMount(
        mount_path='/dev/shm', name='shared-memory'))
	
	# add image pull secrets to pull docker images from private registries
    # this is an existing k8s secret
    registry_secret_name = "registry-secret"
    dsl.get_pipeline_conf().set_image_pull_secrets(
        [k8s_client.V1ObjectReference(name=registry_secret_name)])


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(pipeline, __file__ + '.yaml')