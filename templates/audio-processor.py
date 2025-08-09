import struct
from flask import Flask, request, jsonify

app = Flask(__name__)

# The maximum value for a signed 16-bit integer.
MAX_16BIT_INT = 32767

@app.route('/process_audio', methods=['POST'])
def process_audio():
    """
    Receives a binary audio stream, converts it from 32-bit floats
    to 16-bit integers, and returns the new binary stream.
    """
    if not request.data:
        return jsonify({"error": "No audio data received."}), 400

    try:
        # Unpack the raw binary data into a list of 32-bit floats.
        num_floats = len(request.data) // 4
        float_data = struct.unpack(f'<{num_floats}f', request.data)

        # Scale and convert the floats to 16-bit integers.
        # This mirrors the logic in your JavaScript code.
        int16_data = [
            int(max(-1.0, min(1.0, n)) * MAX_16BIT_INT)
            for n in float_data
        ]

        # Pack the new 16-bit integers back into a binary stream.
        packed_int16 = struct.pack(f'<{len(int16_data)}h', *int16_data)

        # Return the binary data directly with the appropriate MIME type.
        return app.response_class(
            packed_int16,
            mimetype='application/octet-stream'
        )

    except Exception as e:
        # Handle any unexpected errors, such as malformed data.
        return jsonify({"error": f"An internal server error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)

# // audioProcessor.js
# const MAX_16BIT_INT = 32767

# class AudioProcessor extends AudioWorkletProcessor {
#   process(inputs) {
#     try {
#       const input = inputs[0]
#       if (!input || input.length === 0) throw new Error('No input')

#       const channelData = input[0]
#       if (!channelData || channelData.length === 0) throw new Error('No channelData')

#       const float32Array = Float32Array.from(channelData)
#       const int16Array = Int16Array.from(
#         float32Array.map((n) => Math.max(-1, Math.min(1, n)) * MAX_16BIT_INT)
#       )

#       const buffer = int16Array.buffer
#       this.port.postMessage({ audio_data: buffer })

#       return true
#     } catch (error) {
#       console.error('AudioProcessor Error:', error)
#       return false
#     }
#   }
# }

# registerProcessor('audio-processor', AudioProcessor)
