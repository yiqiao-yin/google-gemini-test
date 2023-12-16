import streamlit as st
from PIL import Image
import io
import base64
import requests
import os

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
def call_gemini_api(image_base64, api_key):
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "contents": [
            {
                "parts": [
                    {"text": "What is this picture?"},
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            }
        ]
    }
    response = requests.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/gemini-pro-vision:generateContent?key={api_key}',
        headers=headers,
        json=data
    )
    return response.json()

# Main function of the Streamlit app
def main():
    st.title("Image Capture, Analysis and Save Application")

    # Streamlit widget to capture an image from the user's webcam
    image = st.camera_input("Take a picture")

    if image is not None:
        # Display the captured image
        st.image(image, caption='Captured Image', use_column_width=True)

        # Convert the image to PIL format and resize
        pil_image = Image.open(image)
        resized_image = resize_image(pil_image)

        # Convert the resized image to base64
        image_base64 = convert_image_to_base64(resized_image)

        # API Key (You should set this in your environment variables)
        api_key = st.secrets["PALM_API_KEY"]

        if api_key:
            # Make API call
            response = call_gemini_api(image_base64, api_key)

            # Display the response
            if response['candidates'][0]['content']['parts'][0]['text']:
                text_from_response = response['candidates'][0]['content']['parts'][0]['text']
                st.write(text_from_response)
            else:
                st.write("No response from API.")
        else:
            st.write("API Key is not set. Please set the API Key.")

if __name__ == "__main__":
    main()
