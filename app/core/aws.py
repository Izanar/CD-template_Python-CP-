import aioboto3


def setup_s3_bucket(config):
    return aioboto3.Session(
        aws_access_key_id=config.s3_config.access_key,
        aws_secret_access_key=config.s3_config.secret_key,
        region_name=config.s3_config.region,
    )
