"""
Purpose
An AWS lambda function that analyzes documents with Amazon Textract.
"""
import json
import base64
import logging
import boto3

from botocore.exceptions import ClientError

# Set up logging.
logger = logging.getLogger(__name__)

# Get the boto3 client.
textract_client = boto3.client("textract")


def lambda_handler(event, context):
    """
    Lambda handler function
    param: event: The event object for the Lambda function.
    param: context: The context object for the lambda function.
    return: The list of Block objects recognized in the document
    passed in the event object.
    """

    # raw_image = json.loads(event['body'])['image']
    # message = f"i love {country}"

    # return message

    try:
        # Determine document source.
        # event['image'] = event["queryStringParameters"]['image']
        # event['image'] = json.loads(event['body'])["queryStringParameters"]['image']
        event["image"] = json.loads(event["body"])["image"]
        if "image" in event:
            # Decode the image
            image_bytes = event["image"].encode("utf-8")
            img_b64decoded = base64.b64decode(image_bytes)
            image = {"Bytes": img_b64decoded}

        elif "S3Object" in event:
            image = {
                "S3Object": {
                    "Bucket": event["S3Object"]["Bucket"],
                    "Name": event["S3Object"]["Name"],
                }
            }

        else:
            raise ValueError(
                "Invalid source. Only image base 64 encoded image bytes or S3Object are supported."
            )

        # Analyze the document.
        response = textract_client.detect_document_text(Document=image)

        # Get the Blocks
        blocks = response["Blocks"]

        lambda_response = {"statusCode": 200, "body": json.dumps(blocks)}

    except ClientError as err:
        error_message = "Couldn't analyze image. " + err.response["Error"]["Message"]

        lambda_response = {
            "statusCode": 400,
            "body": {
                "Error": err.response["Error"]["Code"],
                "ErrorMessage": error_message,
            },
        }
        logger.error(
            "Error function %s: %s", context.invoked_function_arn, error_message
        )

    except ValueError as val_error:
        lambda_response = {
            "statusCode": 400,
            "body": {"Error": "ValueError", "ErrorMessage": format(val_error)},
        }
        logger.error(
            "Error function %s: %s", context.invoked_function_arn, format(val_error)
        )

    # Create return body
    http_resp = {}
    http_resp["statusCode"] = 200
    http_resp["headers"] = {}
    http_resp["headers"]["Content-Type"] = "application/json"
    http_resp["body"] = json.dumps(lambda_response)

    return http_resp
