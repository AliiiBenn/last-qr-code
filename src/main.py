import os
import core.encoder as encoder
import core.decoder as decoder
import core.image_utils as image_utils
import core.protocol_config as pc

def main():
    print("Starting main execution...")
    message_to_encode = "Hello World"
    ecc_percentage = pc.DEFAULT_ECC_LEVEL_PERCENT
    output_directory = "images_generes"
    output_image_filename = os.path.join(output_directory, "test_output_from_main.png")
    cell_size = pc.DEFAULT_CELL_PIXEL_SIZE

    # Créer le dossier de sortie s'il n'existe pas
    os.makedirs(output_directory, exist_ok=True)
    print(f"Output directory '{output_directory}' ensured.")

    try:
        print(f"Encoding message: '{message_to_encode}' with ECC {ecc_percentage}%")
        bit_matrix = encoder.encode_message_to_matrix(
            message_text=message_to_encode, 
            ecc_level_percent=ecc_percentage,
            custom_xor_key_str=None # Laisser la clé être générée
        )
        print("Message encoded to bit matrix successfully.")

        print(f"Generating image with cell size {cell_size}px...")
        image_utils.create_protocol_image(
            bit_matrix=bit_matrix, 
            cell_pixel_size=cell_size, 
            output_filename=output_image_filename
        )
        print(f"SUCCESS: Image generated and saved to '{os.path.abspath(output_image_filename)}'")
    
    except ValueError as ve:
        print(f"ERROR (ValueError) during ENCODING: {ve}")
        print("This might be due to the message being too long for the current matrix dimensions and ECC level.")
    except FileNotFoundError as fnfe:
        print(f"ERROR (FileNotFoundError): {fnfe}. Check if Pillow is installed and paths are correct.")
    except Exception as e:
        print(f"AN UNEXPECTED ERROR OCCURRED: {e}")
        import traceback
        traceback.print_exc()
        return # Exit if encoding failed

    # --- Attempt to Decode the Generated Image ---
    print("\n--- STARTING DECODING PROCESS ---")
    try:
        decoded_message = decoder.decode_image_to_message(output_image_filename)
        print(f"SUCCESS: Decoded message: '{decoded_message}'")
        
        if decoded_message == message_to_encode:
            print("VERIFICATION: Decoded message MATCHES the original encoded message.")
        else:
            print("VERIFICATION ERROR: Decoded message DOES NOT MATCH the original.")
            print(f"Original: '{message_to_encode}'")
            print(f"Decoded:  '{decoded_message}'")
            
    except FileNotFoundError as fnfe:
        print(f"DECODING ERROR (FileNotFoundError): {fnfe}")
    except ValueError as ve:
        print(f"DECODING ERROR (ValueError): {ve}")
    except Exception as e:
        print(f"AN UNEXPECTED DECODING ERROR OCCURRED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
