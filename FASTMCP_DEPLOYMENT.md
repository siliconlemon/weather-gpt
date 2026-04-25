# FastMCP Cloud Deployment Guide

## Your GitHub Repository
✅ **Repository Created:** https://github.com/jezweb/weather-mcp-server

## Step-by-Step Deployment to FastMCP Cloud

### 1. Sign in to FastMCP Cloud
1. Visit https://fastmcp.cloud
2. Click "Sign in with GitHub"
3. Authorize FastMCP to access your repositories

### 2. Create New Project
1. Click "Create Project" or "New Project"
2. You'll see a list of your GitHub repositories
3. Select **weather-mcp-server** from the list

### 3. Configure Your Project

Fill in the following settings:

#### Basic Configuration:
- **Project Name:** `weather-server` (or your preferred name)
- **Server Entrypoint:** `weather_server.py`
- **Python Version:** 3.11 (or latest available)

#### Environment Variables (IMPORTANT):
Click "Add Environment Variable" and add:

| Variable Name | Value | Description |
|--------------|-------|-------------|
| `API_KEY` | `e1549ae776638792c28052a7856357c5` | Your OpenWeatherMap API key |
| `DEFAULT_UNITS` | `metric` | Or `imperial` for Fahrenheit |
| `CACHE_TTL` | `600` | Cache duration (10 minutes) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MAX_DAILY_CALLS` | `1000` | API rate limit |

### 4. Deploy
1. Review your configuration
2. Click "Deploy"
3. Wait for the deployment to complete (usually 1-2 minutes)
4. You'll receive a URL like: `https://weather-server.fastmcp.app/mcp`

### 5. Connect to Claude Desktop

#### Option A: Automatic Installation
```bash
fastmcp install claude-desktop https://weather-server.fastmcp.app/mcp
```

#### Option B: Manual Configuration
1. Open Claude Desktop settings
2. Navigate to MCP Servers configuration
3. Add this configuration:

```json
{
  "mcpServers": {
    "weather": {
      "url": "https://weather-server.fastmcp.app/mcp",
      "transport": "http"
    }
  }
}
```

Replace `weather-server` with your actual project name if different.

### 6. Verify Deployment

In Claude Desktop, test the connection:
```
"What's the current weather in London?"
```

The weather server should respond with current conditions.

## Features Available After Deployment

Once deployed, you can use these commands in Claude:

- **Current Weather:** "What's the weather in Paris?"
- **Forecast:** "Show me the 5-day forecast for New York"
- **Multiple Cities:** "What's the weather like in London? How about Tokyo and Sydney?"
- **Air Quality:** "Check air quality in Beijing"
- **Search Locations:** "Find all cities named Springfield"
- **ZIP Code Weather:** "Weather for ZIP code 10001"

## Deployment Settings

### Automatic Features:
- ✅ Auto-deploy on push to main branch
- ✅ PR preview deployments
- ✅ HTTPS/SSL included
- ✅ Global CDN distribution
- ✅ Automatic scaling

### Management:
- View logs at: https://fastmcp.cloud/projects/weather-server/logs
- Monitor usage at: https://fastmcp.cloud/projects/weather-server/analytics
- Update environment variables without redeploying

## Troubleshooting

### If deployment fails:
1. Check that `weather_server.py` is in the root directory
2. Verify all dependencies are in `requirements.txt`
3. Check logs for specific error messages

### If connection fails in Claude:
1. Ensure the URL ends with `/mcp`
2. Verify transport is set to `"http"`
3. Restart Claude Desktop after configuration

### API Key Issues:
- The provided API key (e1549ae776638792c28052a7856357c5) has 1000 calls/day
- If you exceed the limit, get your own free key at https://openweathermap.org/api_keys
- Update the API_KEY environment variable in FastMCP Cloud settings

## Next Steps

1. **Customize:** Modify `weather_server.py` to add more features
2. **Monitor:** Check usage statistics in FastMCP Cloud dashboard
3. **Scale:** Upgrade to paid OpenWeatherMap tier for more API calls
4. **Extend:** Add more weather APIs or data sources

## Support

- FastMCP Cloud Docs: https://docs.fastmcp.com
- OpenWeatherMap API: https://openweathermap.org/api
- GitHub Repo: https://github.com/jezweb/weather-mcp-server

---

**Your server is ready to deploy!** Follow the steps above to get your weather MCP server live on FastMCP Cloud.