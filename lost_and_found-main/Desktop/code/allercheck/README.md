# allercheck - Google Cloud Vision API Integration

## Prerequisites

1. Google Cloud Platform account
2. Billing enabled for your project
3. Google Cloud Vision API enabled
4. Service account with appropriate permissions
5. Service account key file (JSON)

## Setup Instructions

### 1. Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable billing for the project

### 2. Enable the Vision API

1. In the Google Cloud Console, navigate to "APIs & Services" > "Library"
2. Search for "Cloud Vision API"
3. Click on "Cloud Vision API" and then click "Enable"

### 3. Create a Service Account

1. Go to "IAM & Admin" > "Service Accounts"
2. Click "Create Service Account"
3. Give it a name (e.g., "allercheck-vision")
4. Assign the "roles/vision.user" role or "roles/editor" role
5. Click "Done"

### 4. Create and Download Service Account Key

1. On the Service Accounts page, click on your newly created service account
2. Go to the "Keys" tab
3. Click "Add Key" > "Create new key"
4. Select "JSON" format and click "Create"
5. Save the downloaded JSON file securely

### 5. Configure Authentication

There are two ways to configure authentication:

#### Option A: Environment Variable (Recommended)

1. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your JSON key file:

   On Windows:
   ```
   set GOOGLE_APPLICATION_CREDENTIALS=C:\path\to\your\service-account-key.json
   ```

   On macOS/Linux:
   ```
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/service-account-key.json
   ```

#### Option B: Specify in Code

Modify the `api/analyze-image.php` file to specify the key file path directly:

```php
$imageAnnotator = new ImageAnnotatorClient([
    'keyFilePath' => '/path/to/your/service-account-key.json'
]);
```

## How It Works

The integration works as follows:

1. User uploads an image through the web interface
2. The image is sent to the backend API (`api/analyze-image.php`)
3. The API calls Google Cloud Vision API to analyze the image
4. Google Cloud Vision returns detected labels/objects in the image
5. The API filters food-related labels and checks them against user's allergies
6. Results are returned to the frontend showing if allergens were detected

## Cost Considerations

Google Cloud Vision API has a generous free tier:
- First 1000 units per month are free
- After that, $1.50 per 1000 units

A typical label detection request counts as 1 unit, so you can analyze approximately 1000 images per month for free.