const { chromium } = require('playwright');  // Import playwright library

async function chatWithGPT(query) {
    // Step 1: Launch the browser
    const browser = await chromium.launch({ headless: false });  // Change to true if you don't want to see the browser UI
    const page = await browser.newPage();

    // Step 2: Navigate to ChatGPT (or your preferred URL)
    await page.goto('https://chat.openai.com/');

    // Step 3: Wait for the login screen (if needed) and log in
    // Assuming you've already logged in manually or have a way to bypass this step
    
    // Step 4: Wait for the chat input box to load
    await page.waitForSelector('textarea');  // Chat input area, adjust if necessary

    // Step 5: Type the question into the input area and send it
    await page.fill('textarea', query);  // Type the question
    await page.keyboard.press('Enter');  // Simulate pressing the Enter key

    // Step 6: Wait for the response to load
    await page.waitForSelector('.text-base');  // Adjust selector for where the response appears

    // Step 7: Extract the response
    const response = await page.$eval('.text-base', (el) => el.innerText);  // Capture the response from the chat

    console.log('ChatGPT response:', response);  // Output the response

    // Step 8: Close the browser
    await browser.close();
}

// Call the function with your question
chatWithGPT('What is the capital of France?');