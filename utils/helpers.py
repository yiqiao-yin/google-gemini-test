import base64
import io
import json
import os
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st
from PIL import Image
import google.generativeai as palm
from pypdf import PdfReader
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
)
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


# API Key (You should set this in your environment variables)
api_key = st.secrets["PALM_API_KEY"]
palm.configure(api_key=api_key)


# Function to convert the image to bytes for download
def convert_image_to_bytes(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return buffered.getvalue()


# Function to resize the image
def resize_image(image):
    return image.resize((512, int(image.height * 512 / image.width)))


# Function to convert the image to base64
def convert_image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


# Function to make an API call to Palm
def call_palm(prompt: str) -> str:
    completion = palm.generate_text(
        model="models/text-bison-001",
        prompt=prompt,
        temperature=0,
        max_output_tokens=800,
    )

    return completion.result


# Function to make an API call to Google's Gemini API
def call_gemini_api(image_base64, api_key=api_key, prompt="What is this picture?"):
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}},
                ]
            }
        ]
    }
    response = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}",
        headers=headers,
        json=data,
    )
    return response.json()


def safely_get_text(response):
    try:
        response
    except Exception as e:
        print(f"An error occurred: {e}")

    # Return None or a default value if the path does not exist
    return None


def post_request_and_parse_response(
    url: str, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Sends a POST request to the specified URL with the given payload,
    then parses the byte response to a dictionary.

    Args:
    url (str): The URL to which the POST request is sent.
    payload (Dict[str, Any]): The payload to send in the POST request.

    Returns:
    Dict[str, Any]: The parsed dictionary from the response.
    """
    # Set headers for the POST request
    headers = {"Content-Type": "application/json"}

    # Send the POST request and get the response
    response = requests.post(url, json=payload, headers=headers)

    # Extract the byte data from the response
    byte_data = response.content

    # Decode the byte data to a string
    decoded_string = byte_data.decode("utf-8")

    # Convert the JSON string to a dictionary
    dict_data = json.loads(decoded_string)

    return dict_data


def extract_line_items(input_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extracts items with "BlockType": "LINE" from the provided JSON data.

    Args:
    input_data (Dict[str, Any]): The input JSON data as a dictionary.

    Returns:
    List[Dict[str, Any]]: A list of dictionaries with the extracted data.
    """
    # Initialize an empty list to hold the extracted line items
    line_items: List[Dict[str, Any]] = []

    # Get the list of items from the 'body' key in the input data
    body_items = json.loads(input_data.get("body", "[]"))

    # Iterate through each item in the body
    for item in body_items:
        # Check if the BlockType of the item is 'LINE'
        if item.get("BlockType") == "LINE":
            # Add the item to the line_items list
            line_items.append(item)

    return line_items


def rag(query: str, retrieved_documents: list, api_key: str = api_key) -> str:
    """
    Function to process a query and a list of retrieved documents using the Gemini API.

    Args:
    query (str): The user's query or question.
    retrieved_documents (list): A list of documents retrieved as relevant information to the query.
    api_key (str): API key for accessing the Gemini API. Default is a predefined 'api_key'.

    Returns:
    str: The cleaned output from the Gemini API response.
    """
    # Combine the retrieved documents into a single string, separated by two newlines.
    information = "\n\n".join(retrieved_documents)

    # Format the query and combined information into a single message.
    messages = f"Question: {query}. \n Information: {information}"

    # Call the Gemini API with the formatted message and the API key.
    gemini_output = call_palm(prompt=messages)

    # Placeholder for processing the Gemini output. Currently, it simply assigns the raw output to 'cleaned_output'.
    cleaned_output = gemini_output  # ["candidates"][0]["content"]["parts"][0]["text"]

    return cleaned_output
