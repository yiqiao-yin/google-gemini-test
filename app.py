import base64
import io
import os

import requests
import streamlit as st
from PIL import Image


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
def call_gemini_api(image_base64, api_key, prompt="What is this picture?"):
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


# Main function of the Streamlit app
def main():
    st.title("Image Capture, Analysis and Save Application")

    # Streamlit widget to capture an image from the user's webcam
    image = st.sidebar.camera_input("Take a picture 📸")

    # Add instruction
    st.sidebar.markdown(
        """
            # 🌟 How to Use the App 🌟

            Follow these simple steps to interact with the app and have a chat with Gemini about your picture:

            1. **Capture a Moment** 📸
            - Go to the **sidebar**.
            - Click on **"Take a picture"** to capture an image using your webcam.

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

        # API Key (You should set this in your environment variables)
        api_key = st.secrets["PALM_API_KEY"]

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
                        # Handle the case where the text does not exist
                        st.write(
                            "Gemini:", "No output found. Please ask another question."
                        )

            else:
                st.write("No response from API.")
        else:
            st.write("API Key is not set. Please set the API Key.")


if __name__ == "__main__":
    main()
