import kfp.dsl as dsl
import kfp


@dsl.pipeline(
    name='kubeflow-barebone-demo',
    description='kubeflow demo with minimal setup'
)
def pipeline(
    model_save_path="s3://fancy-model/version1",
    learning_rate=1e-3,
    num_layers=10,
):
    # Step 1: training component
    training = dsl.ContainerOp(
        name='training',
        image='ubuntu:latest',
        command=[
            'sh', '-c',
            f'echo "training..." && sleep 10 && echo "{model_save_path}" > /goose.txt'
        ],
        file_outputs={'model_save_path': '/goose.txt'}
    )

    # Step 2: evaluation component
    evaluation = dsl.ContainerOp(
        name='evaluation',
        image='ubuntu:latest',
        command=[
            'sh', '-c',
            'echo "evaluating" && '
            f'echo \'load model from: {training.outputs["model_save_path"]}\' && '
            'sleep 10 && '
            'echo "accuracy: 0.$(shuf -i 0-99 -n 1)" > /accuracy.txt'
        ],
        file_outputs={'accuracy': '/accuracy.txt'}
    )


if __name__ == "__main__":
    kfp.compiler.Compiler().compile(pipeline, 'pipeline.yaml')
