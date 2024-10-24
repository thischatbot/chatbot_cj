
### **Project Plan: Emotion-Based Animatronics Boyfriend Chatbot**

#### **1. Project Overview**
**Project Name**: Emotion Recognition and Animatronics-Based Boyfriend Chatbot  
**Objective**: To develop an AI-powered chatbot that recognizes emotions and integrates animatronics technology to display emotional expressions through eye movements and facial gestures in real time. 

#### **2. Technical Overview**
Key Technologies:
- **OpenAI GPT API**: Emotion recognition and conversation generation.
- **KitsAI Voice Synthesis**: Generating voice responses.
- **STM32-based Servo Motor Control**: Controlling the eyes and facial gestures.
- **Animatronics Design**: Mechanisms for eye movement.

#### **3. Updated LLM Dataset Construction**
- **Dataset based on Korean modern literature** for emotion recognition.
- **Emotional labels** applied to key poetic lines, creating a CSV dataset structure.
  
**Example CSV Structure**:
| Poetic Line | Emotion Label | Poem Title | Poet |
|-------------|---------------|------------|------|
| "Whispering sunlight on the stone wall" | Peace | "The One Outside" | Kim Young-rang |

#### **4. JSON Interaction Log Structure**:
The chatbot stores past interactions in JSON format, which helps it remember prior conversations and generate context-aware responses.

**Example JSON Log**:
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

#### **5. System Architecture**
- **Raspberry Pi 4**: Manages API calls and emotion processing.
- **STM32 Microcontroller**: Controls servo motors for animatronics.
- **Servo Motors**: For controlling eye movements.
- **6-Axis Accelerometer**: For adjusting eye position based on head movement.
- **3D-Printed Eye Structure**: Physical components for realistic eye gestures.

#### **6. Software Overview**
- **OpenAI GPT API**: Handles conversations and emotion analysis.
- **Google Cloud STT**: Speech-to-text processing.
- **KitsAI TTS**: Text-to-speech for chatbot responses.
- **Python on Raspberry Pi**: Manages communication with STM32 and handles interactions.
  
#### **7. Interaction Enhancement**
The chatbot dynamically adjusts eye movements and facial gestures based on conversations, using past interactions stored in JSON to personalize responses.

#### **8. Updated Project Timeline**  
**Month 1**:  
- Integrating Raspberry Pi with OpenAI API, Google STT/TTS, and building the initial conversation system.
  
**Month 2**:  
- Implementing STM32-based servo motor control, developing basic eye movement mechanics.

**Month 3**:  
- Finalizing the animatronics design, integrating emotion recognition with eye movements.
  
**Month 4**:  
- System testing, refining the interaction flow, and gathering feedback from user trials.

