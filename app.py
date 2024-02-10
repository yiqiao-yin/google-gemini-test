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
import pandas as pd
from pypdf import PdfReader
from langchain.text_splitter import (
    RecursiveCharacterTextSplitter,
    SentenceTransformersTokenTextSplitter,
)
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from utils.helpers import *

# API Key (You should set this in your environment variables)
api_key = st.secrets["PALM_API_KEY"]
palm.configure(api_key=api_key)


# Main function of the Streamlit app
def main():
    st.title("Generative AI Demo on Camera Input/Image/PDF 💻")

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

            1) **🌈 User Input Magic**:
            - 📸 **Camera Snap**: Tap to capture a moment with your device's camera. Say cheese!
            - 🖼️ **Image Upload Extravaganza**: Got a cool pic? Upload it from your computer and let the magic begin!
            - 📄 **PDF Adventure**: Use gen AI as ctrl+F to search information on any PDF, like opening a treasure chest of information!

            2) **🤖 AI Interaction Wonderland**:
            - 🌟 **Gemini's AI**: Google's Gemini AI is your companion, ready to dive deep into your uploads.
            - 🌐 **Chroma Database**: As you upload, we're crafting a colorful Chroma database in our secret lab, making your interaction even more awesome!

            3) **💬 Chit-Chat with AI Post-Upload**:
            - 🌍 Once your content is up in the app, ask away! Any question, any time.
            - 💡 Light up the conversation with Gemini AI. It is like having a chat with a wise wizard from the digital realm!

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
                with st.spinner("Wait for it..."):
                    st.write(text_from_response)

                # Text input for the question
                input_prompt = st.text_input(
                    "Type your question here:",
                )
                input_prompt = f"""
                    Try answer user's question {input_prompt}

                    If there's not a confident answer, then add this in the end 'We recommend to verify the image because we do not have a confident answer'. 
                """

                # Display the entered question
                if input_prompt:
                    updated_text_from_response = call_gemini_api(
                        image_base64, api_key, prompt=input_prompt
                    )

                    if updated_text_from_response is not None:
                        # Do something with the text
                        updated_ans = updated_text_from_response["candidates"][0][
                            "content"
                        ]["parts"][0]["text"]
                        with st.spinner("Wait for it..."):
                            st.write(f"Gemini: {updated_ans}")
                    else:
                        st.warning("Check gemini's API.")

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

        # Display PDF
        # displayPDF(file_name)

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
        results_as_table = pd.DataFrame(results)

        # API of a foundation model
        output = rag(query=query, retrieved_documents=retrieved_documents)
        st.write(output)
        st.success("Please see where the chatbot got the information from the document below.👇")
        st.table(results_as_table)


if __name__ == "__main__":
    main()
