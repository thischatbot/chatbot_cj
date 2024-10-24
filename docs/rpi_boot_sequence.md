### **RPi Boot Sequence Document**

#### **Project Overview**
The system is designed to boot up a Raspberry Pi-based AI chatbot with animatronics capabilities. It utilizes real-time emotion analysis, interaction logging, and servo motor control to provide personalized conversation and facial expressions.

#### **1. Hardware Boot Sequence**
- **Step 1**: **Hardware Switch ON**
   - The Raspberry Pi is powered on using a physical switch.
   
- **Step 2**: **Raspberry Pi Booting**
   - The Raspberry Pi begins booting its operating system.
   
- **Step 3**: **System Check with Init.d Scripts**
   - The system checks for the following:
     - **Microphone**: Ensures that the microphone is connected.
     - **Speaker**: Ensures that the speaker is connected.
     - **Wi-Fi/Bluetooth**: Verifies network connectivity.
     - **UART Communication**: Verifies UART communication with the STM32 controller.
     - **SD Card Check**: Verifies that the SD card containing the interaction logs is accessible.

#### **2. Error Handling**
- If any system checks fail, the Raspberry Pi will:
   - Retry connections (e.g., Wi-Fi, Bluetooth, UART).
   - Notify the user of the failure through a **TTS output** or log the error.

#### **3. Reading JSON Interaction Logs**
- The Raspberry Pi accesses the SD card and reads the last conversation logs stored in **JSON format**.
- Example JSON structure:
   ```json
   {
     "last_interaction": {
       "timestamp": "2024-10-24T08:30:00",
       "topic": "Weekend Plans",
       "emotion": "happy",
       "last_message": "Thank you for today!"
     },
     "greeting_options": {
       "morning": ["Good morning!", "Did you have breakfast?"],
       "afternoon": ["Good afternoon!", "How's your day going?"],
       "evening": ["Good evening!", "What did you do today?"]
     }
   }
   ```
   - **Purpose**: Logs the last topic discussed, associated emotion, and previous messages to personalize future interactions.

#### **4. Time-Based Random Greeting**
- Based on the time of day, the chatbot selects an appropriate greeting from the **greeting_options** field in the JSON log.
   - Morning: "Good morning!" or "Did you have breakfast?"
   - Afternoon: "Good afternoon!" or "How's your day going?"
   - Evening: "Good evening!" or "What did you do today?"

#### **5. Boot Completion Signal to STM32**
- Once the Raspberry Pi completes system checks, it sends a **boot completion signal** to the STM32 controller via UART.
   
#### **6. STM32 Acknowledgment**
- The STM32 controller responds with an acknowledgment (ACK) signal.

#### **7. Text-to-Speech (TTS) Greeting**
- After receiving the ACK signal, the Raspberry Pi uses the **TTS system** to output a personalized greeting based on the interaction logs and current time.

#### **8. Animatronics Control**
- Simultaneously, the Raspberry Pi sends a signal to the STM32 to control the servo motors for **facial expressions**, such as a smile or eye movements, depending on the greeting context and emotion analysis.

#### **9. Continuous Monitoring**
- After booting, the system continuously monitors the status of peripherals (microphone, speaker, UART) and interaction logs for the next conversational sequence.

---

### **Enhancements & Suggestions**
- **Custom Greetings**: Based on the previous interaction logs, greetings can be further personalized (e.g., “I remember we talked about [topic] last time. How has that been going?”).
- **Retry & Error Logging**: Implement a retry mechanism for system checks and log any errors encountered during the boot sequence for debugging.


