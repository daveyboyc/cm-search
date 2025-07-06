# 🎯 How to Capture IETF Project Data

## ✅ SUCCESS: The API Request Works!

We successfully made a request to Tableau and got a response, but we need to capture the request when you click on a **specific marker** (not just hover).

## 📋 Step-by-Step Instructions

### 1. **Open the Map**
- Go to: https://public.tableau.com/views/IETFProjectMap/MapDashboard
- Wait for it to fully load (you should see markers on the map)

### 2. **Prepare Network Monitoring**
- Open DevTools (F12)
- Go to **Network** tab
- **Clear the network log** (trash can icon)
- **Filter by "XHR"** to reduce noise

### 3. **Capture the Right Request** 🎯
- **Click directly on a map marker** (not just hover!)
- You should see a tooltip popup with project details
- Look for a new request in Network tab containing:
  - `render-tooltip-server` in the URL
  - Shows as **POST** method
  - Has a response size > 1KB (our test was only 692 bytes)

### 4. **Copy the Request**
- Right-click the `render-tooltip-server` request
- Choose **Copy** → **Copy as cURL**
- The cURL should be much longer than our test one

### 5. **Verify It's the Right Request**
Good signs the request contains data:
- ✅ Response size > 2KB (not 692 bytes)
- ✅ Preview shows HTML content with project info
- ✅ Headers show `content-length` > 2000

## 🔍 What We Found So Far

From your captured request:
- ✅ **Session ID works**: `A8F364831F894B44BCCE6DFAEA5EF166-0:0`
- ✅ **API endpoint responds**: Status 200
- ✅ **Authentication works**: Cookies are valid
- ⚠️ **Empty tooltip**: Shows `tupleId: 0` (no marker selected)

## 🎯 Next Steps

1. **Follow the instructions above** to capture a marker-click request
2. **Paste the new cURL** into our extractor
3. **Run the script** - it should find much more data!

The infrastructure is working perfectly - we just need the request from an actual marker click! 🚀 