import base64
from gtts import gTTS
import io
import json
import os
from typing import Any, Dict, List

import pandas as pd
import requests
import streamlit as st
from PIL import Image

from pypdf import PdfReader
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
)
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction


# API Key (You should set this in your environment variables)
api_key = st.secrets["PALM_API_KEY"]


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


def rag(query, retrieved_documents, api_key=api_key):
    information = "\n\n".join(retrieved_documents)
    messages = f"Question: {query}. \n Information: {information}"
    gemini_output = call_gemini_api(api_key, prompt=messages)
    cleaned_output = gemini_output  # ["candidates"][0]["content"]["parts"][0]["text"]

    return cleaned_output


# Main function of the Streamlit app
def main():
    st.title("Image Capture, Analysis and Save Application")

    # Dropdown for user to choose the input method
    input_method = st.sidebar.selectbox(
        "Choose input method:", ["Camera", "Upload Image", "Upload PDF"]
    )

    image, uploaded_file = None, None
    if input_method == "Camera":
        # Streamlit widget to capture an image from the user's webcam
        image = st.sidebar.camera_input("Take a picture 📸")
    elif input_method == "Upload Image":
        # Create a file uploader in the sidebar
        image = st.sidebar.file_uploader("Upload a JPG image", type=["jpg"])
    elif input_method == "Upload PDF":
        # File uploader widget
        uploaded_file = st.sidebar.file_uploader("Choose a PDF file", type="pdf")

    # Add instruction
    st.sidebar.markdown(
        """
            # 🌟 How to Use the App 🌟

            Follow these simple steps to interact with the app and have a chat with Gemini about your picture:

            1. **Capture a Moment** 📸
            - Go to the **sidebar**.
            - Use dropdown selection to **"Take a picture"** to capture an image using your webcam or **"Upload a file"** from your computer.

            2. **Gemini's Insight** 🔮
            - Once you've taken a picture, just wait a moment.
            - See what **Google's Gemini** AI has to say about your photo as the app processes it.

            3. **Chat with Gemini** 💬
            - Feel free to ask questions or start a conversation about the picture you just took.
            - Let's see what interesting stories Gemini can tell you!

            Enjoy exploring and have fun! 😄🎉
        """
    )

    if image is not None:
        # Display the captured image
        st.image(image, caption="Captured Image", use_column_width=True)

        # Convert the image to PIL format and resize
        pil_image = Image.open(image)
        resized_image = resize_image(pil_image)

        # Convert the resized image to base64
        image_base64 = convert_image_to_base64(resized_image)

        # OCR by API Call of AWS Textract via Post Method
        if input_method == "Upload Image":
            url = "https://2tsig211e0.execute-api.us-east-1.amazonaws.com/my_textract"
            payload = {"image": image_base64}
            result_dict = post_request_and_parse_response(url, payload)
            output_data = extract_line_items(result_dict)
            df = pd.DataFrame(output_data)

            # Using an expander to hide the json
            with st.expander("Show/Hide Raw Json"):
                st.write(result_dict)

            # Using an expander to hide the table
            with st.expander("Show/Hide Table"):
                st.table(df)

        if api_key:
            # Make API call
            response = call_gemini_api(image_base64, api_key)

            # Display the response
            if response["candidates"][0]["content"]["parts"][0]["text"]:
                text_from_response = response["candidates"][0]["content"]["parts"][0][
                    "text"
                ]
                st.write(text_from_response)

                # Text input for the question
                input_prompt = st.text_input("Type your question here:")
                if input_method == "Upload":
                    input_prompt = str(
                        f"""
                            Question: {input_prompt} based on the information here: {df}
                        """
                    )
                else:
                    input_prompt = str(
                        f"""
                            Answer the question: {input_prompt}
                        """
                    )

                # Display the entered question
                if input_prompt:
                    updated_text_from_response = call_gemini_api(
                        image_base64, api_key, prompt=input_prompt
                    )

                    updated_text_from_response = updated_text_from_response[
                        "candidates"
                    ][0]["content"]["parts"][0]["text"]
                    text = safely_get_text(updated_text_from_response)
                    if text is not None:
                        # Do something with the text
                        updated_ans = updated_text_from_response["candidates"][0][
                            "content"
                        ]["parts"][0]["text"]
                        st.write("Gemini:", updated_ans)

            else:
                st.write("No response from API.")
        else:
            st.write("API Key is not set. Please set the API Key.")

    # File uploader widget
    if uploaded_file is not None:
        # To read file as bytes:
        bytes_data = uploaded_file.getvalue()
        st.success("Your PDF is uploaded successfully.")

        # Get the file name
        file_name = uploaded_file.name

        # Save the file temporarily
        with open(file_name, "wb") as f:
            f.write(uploaded_file.getbuffer())

        # Read file
        reader = PdfReader(file_name)
        pdf_texts = [p.extract_text().strip() for p in reader.pages]

        # Filter the empty strings
        pdf_texts = [text for text in pdf_texts if text]
        st.success("PDF extracted successfully.")

        # Split the texts
        character_splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", ". ", " ", ""], chunk_size=1000, chunk_overlap=0
        )
        character_split_texts = character_splitter.split_text("\n\n".join(pdf_texts))
        st.success("Texts splitted successfully.")

        # Tokenize it
        st.warning("Start tokenzing ...")
        token_splitter = SentenceTransformersTokenTextSplitter(
            chunk_overlap=0, tokens_per_chunk=256
        )
        token_split_texts = []
        for text in character_split_texts:
            token_split_texts += token_splitter.split_text(text)
        st.success("Tokenized successfully.")

        # Add to vector database
        embedding_function = SentenceTransformerEmbeddingFunction()
        chroma_client = chromadb.Client()
        chroma_collection = chroma_client.create_collection(
            "tmp", embedding_function=embedding_function
        )
        ids = [str(i) for i in range(len(token_split_texts))]
        chroma_collection.add(ids=ids, documents=token_split_texts)
        st.success("Vector database loaded successfully.")

        # User input
        query = st.text_input("Ask me anything!", "What is the document about?")
        results = chroma_collection.query(query_texts=[query], n_results=5)
        retrieved_documents = results["documents"][0]

        # API of a foundation model
        output = rag(query=query, retrieved_documents=retrieved_documents)
        st.write(output)


if __name__ == "__main__":
    main()
