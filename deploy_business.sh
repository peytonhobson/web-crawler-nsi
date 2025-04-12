#!/bin/bash
# Script to generate and deploy business-specific configurations to Render

# Display usage if no arguments are provided
if [ $# -lt 2 ]; then
  echo "Usage: $0 <business_name> <config_yaml_path> [render_token]"
  echo ""
  echo "Example: $0 westhills examples/winery_config.yaml"
  echo ""
  echo "Parameters:"
  echo "  business_name      - Unique name for the business (no spaces, used in service names)"
  echo "  config_yaml_path   - Path to the YAML configuration file for this business"
  echo "  render_token       - Optional: Render API token for direct deployment"
  exit 1
fi

# Get parameters
BUSINESS_NAME=$1
CONFIG_FILE=$2
RENDER_TOKEN=$3

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
  echo "Error: Configuration file '$CONFIG_FILE' not found."
  exit 1
fi

# Create business-specific directories if they don't exist
mkdir -p "configs/$BUSINESS_NAME"

# Copy the business configuration to the configs directory
cp "$CONFIG_FILE" "configs/$BUSINESS_NAME/config.yaml"

# Create a business-specific render.yaml file from the template
mkdir -p "render_configs"
RENDER_CONFIG="render_configs/render_${BUSINESS_NAME}.yaml"

echo "Generating Render configuration for $BUSINESS_NAME..."
cat render.yaml | sed "s/\${BUSINESS_NAME}/$BUSINESS_NAME/g" | sed "s|\${BUSINESS_CONFIG}|configs/$BUSINESS_NAME/config.yaml|g" > "$RENDER_CONFIG"

echo "Created Render configuration at: $RENDER_CONFIG"

# If Render token is provided, deploy directly to Render
if [ -n "$RENDER_TOKEN" ]; then
  echo "Deploying to Render..."
  
  # Check if render-cli is installed
  if ! command -v render &> /dev/null; then
    echo "Render CLI not found. Installing..."
    npm install -g @render/cli
  fi
  
  # Deploy using Render CLI
  render deploy --config "$RENDER_CONFIG" --api-key "$RENDER_TOKEN"
else
  echo ""
  echo "To deploy to Render manually:"
  echo "1. Go to Render Dashboard: https://dashboard.render.com/"
  echo "2. Create a new 'Blueprint' deployment"
  echo "3. Connect your repository"
  echo "4. Specify the Render YAML path as: $RENDER_CONFIG"
  echo ""
  echo "Or install render-cli and run:"
  echo "render deploy --config $RENDER_CONFIG --api-key YOUR_RENDER_TOKEN"
fi

echo "Done!" 