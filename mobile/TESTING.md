# How to Test the Mobile App on Your Phone

You can easily test the Bacterial Colony Counter app on your physical iPhone or Android device using **Expo Go**.

## Prerequisites

1.  **Install Expo Go** on your phone:
    - [iOS App Store](https://apps.apple.com/us/app/expo-go/id982107779)
    - [Android Play Store](https://play.google.com/store/apps/details?id=host.exp.exponent)
2.  Ensure your **Phone** and **Laptop** are on the **SAME Wi-Fi Network**.

## Steps to Run

1.  **Start the Mobile Server** (if not already running):

    - Open a new terminal.
    - Navigate to the mobile folder: `cd mobile`
    - Run: `npx expo start`

    _(Note: Do not use `npm run web` for phone testing, just standard `npx expo start`)_

2.  **Scan the QR Code**:

    - Look at the terminal output on your laptop. You should see a large QR code.
    - **Android**: Open the **Expo Go** app and tap "Scan QR Code". Scan the code from the terminal.
    - **iOS**: Open your **Camera** app and verify scan the QR code. Tap the notification to open in Expo Go.

3.  **Troubleshooting**:
    - **"Could not connect"**: This usually means your devices can't see each other.
      - Try running `npx expo start --tunnel`. This creates a global tunnel (slower but works everywhere).
    - **API Errors**: If the app loads but uploading fails:
      - The app tries to connect to your laptop's backend (`http://<your-laptop-ip>:8000`).
      - Ensure your backend is running (`python main.py`).
      - Ensure your firewall allows incoming connections on port 8000.

## App Features to Try

- **Dark Mode**: Go to **Settings** (Sidebar) -> enable **Dark Mode**. The entire app should switch to a dark Zinc theme.
- **History**: Analyze a few images. Go to **History** to see your past results saved locally.
- **Upload**: Use "Open Camera" to take a real photo of a petri dish!
