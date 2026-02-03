#!/usr/bin/env bash
set -euo pipefail

# Generate Architecture Diagram for Enterprise Foundry ACA Setup
# Output: ../architecture_diagram.svg (in project root)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_FILE="$SCRIPT_DIR/../architecture_diagram.svg"

cat > "$OUTPUT_FILE" << 'SVGEOF'
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 1000" font-family="Segoe UI, Arial, sans-serif">
  <defs>
    <!-- Gradients -->
    <linearGradient id="vnetGreen" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#107C10;stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:#107C10;stop-opacity:0.25" />
    </linearGradient>
    <linearGradient id="subnetBlue" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#0078D4;stop-opacity:0.1" />
      <stop offset="100%" style="stop-color:#0078D4;stop-opacity:0.2" />
    </linearGradient>
    <linearGradient id="hubOrange" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#FF8C00;stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:#FF8C00;stop-opacity:0.25" />
    </linearGradient>
    <linearGradient id="onpremPurple" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#8661C5;stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:#8661C5;stop-opacity:0.25" />
    </linearGradient>
    
    <!-- Arrow marker -->
    <marker id="arrowhead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#666" />
    </marker>
  </defs>

  <!-- Background -->
  <rect width="1500" height="1000" fill="#f8f9fa"/>
  
  <!-- Title -->
  <text x="750" y="35" text-anchor="middle" font-size="24" font-weight="bold" fill="#333">Enterprise Foundry - ACA Sandbox Architecture</text>
  <text x="750" y="58" text-anchor="middle" font-size="14" fill="#666">Azure Container Apps with VNet Integration &amp; Private Endpoints</text>

  <!-- ==================== Hub VNet (Top Center) ==================== -->
  <g id="hub-vnet">
    <rect x="490" y="85" width="220" height="120" rx="8" fill="url(#hubOrange)" stroke="#FF8C00" stroke-width="2"/>
    <text x="600" y="110" text-anchor="middle" font-size="13" font-weight="bold" fill="#FF8C00">Hub VNet</text>
    <text x="600" y="128" text-anchor="middle" font-size="10" fill="#666">vnet-hub (10.0.0.0/16)</text>
    <text x="600" y="143" text-anchor="middle" font-size="9" fill="#888">(Corporate Network Simulation)</text>
    
    <!-- Gateway icon -->
    <rect x="545" y="155" width="110" height="35" rx="4" fill="#fff" stroke="#FF8C00" stroke-width="1"/>
    <text x="600" y="173" text-anchor="middle" font-size="9" fill="#FF8C00">🌐 VPN/ER Gateway</text>
  </g>

  <!-- ==================== Sandbox VNet (Left) ==================== -->
  <g id="sandbox-vnet">
    <rect x="50" y="260" width="580" height="400" rx="8" fill="url(#vnetGreen)" stroke="#107C10" stroke-width="2"/>
    <text x="340" y="285" text-anchor="middle" font-size="13" font-weight="bold" fill="#107C10">Sandbox VNet</text>
    <text x="340" y="303" text-anchor="middle" font-size="10" fill="#666">vnet-foundry-sbx (10.7.0.0/26) | rg-foundry-sbx-net</text>

    <!-- ACA Infrastructure Subnet -->
    <g id="aca-subnet">
      <rect x="70" y="320" width="540" height="160" rx="6" fill="url(#subnetBlue)" stroke="#0078D4" stroke-width="1.5" stroke-dasharray="4,2"/>
      <text x="340" y="340" text-anchor="middle" font-size="11" font-weight="bold" fill="#0078D4">snet-aca-infra (10.7.0.0/27)</text>
      
      <!-- ACA Environment -->
      <rect x="90" y="355" width="500" height="110" rx="5" fill="#fff" stroke="#0078D4" stroke-width="2"/>
      <text x="340" y="375" text-anchor="middle" font-size="10" font-weight="bold" fill="#0078D4">Container Apps Environment: cae-foundry-sbx (Internal LB)</text>
      
      <!-- Container Apps -->
      <rect x="110" y="390" width="220" height="60" rx="4" fill="#E6F2FF" stroke="#0078D4" stroke-width="1"/>
      <text x="220" y="410" text-anchor="middle" font-size="9" font-weight="bold" fill="#0078D4">📦 aca-onprem-connectivity-test</text>
      <text x="220" y="425" text-anchor="middle" font-size="8" fill="#666">Alpine + curl | Tests on-prem</text>
      <text x="220" y="438" text-anchor="middle" font-size="8" fill="#888">Uses: id-aca-acr-pull identity</text>
      
      <rect x="350" y="390" width="220" height="60" rx="4" fill="#E6F2FF" stroke="#0078D4" stroke-width="1"/>
      <text x="460" y="410" text-anchor="middle" font-size="9" font-weight="bold" fill="#0078D4">📦 aca-pe-storage-test</text>
      <text x="460" y="425" text-anchor="middle" font-size="8" fill="#666">Storage connectivity test</text>
      <text x="460" y="438" text-anchor="middle" font-size="8" fill="#888">Tests Private Endpoints</text>
    </g>

    <!-- Private Endpoints Subnet -->
    <g id="pe-subnet">
      <rect x="70" y="495" width="540" height="150" rx="6" fill="#FFF5E6" stroke="#FF8C00" stroke-width="1.5" stroke-dasharray="4,2"/>
      <text x="340" y="515" text-anchor="middle" font-size="10" font-weight="bold" fill="#FF8C00">snet-private-endpoints (10.7.0.32/28)</text>
      
      <!-- Private Endpoint - Blob -->
      <rect x="90" y="530" width="150" height="50" rx="4" fill="#fff" stroke="#FF8C00" stroke-width="1"/>
      <text x="165" y="548" text-anchor="middle" font-size="9" fill="#FF8C00">🔒 pe-blob</text>
      <text x="165" y="562" text-anchor="middle" font-size="8" fill="#888">&lt;storage-account&gt;</text>
      <text x="165" y="574" text-anchor="middle" font-size="7" fill="#888">Blob Storage</text>
      
      <!-- Private Endpoint - ACR -->
      <rect x="260" y="530" width="150" height="50" rx="4" fill="#fff" stroke="#0078D4" stroke-width="1"/>
      <text x="335" y="548" text-anchor="middle" font-size="9" fill="#0078D4">🔒 pe-acr</text>
      <text x="335" y="562" text-anchor="middle" font-size="8" fill="#888">&lt;container-registry&gt;</text>
      <text x="335" y="574" text-anchor="middle" font-size="7" fill="#888">Container Registry</text>

      <!-- Managed Identity -->
      <rect x="430" y="530" width="160" height="50" rx="4" fill="#fff" stroke="#5C2D91" stroke-width="1"/>
      <text x="510" y="548" text-anchor="middle" font-size="9" fill="#5C2D91">🔑 id-aca-acr-pull</text>
      <text x="510" y="562" text-anchor="middle" font-size="8" fill="#888">Managed Identity</text>
      <text x="510" y="574" text-anchor="middle" font-size="7" fill="#888">AcrPull Role</text>
    </g>
  </g>

  <!-- ==================== Azure Services (Below Sandbox VNet - aligned with PEs) ==================== -->
  <g id="azure-services">
    <!-- Storage Account (below pe-blob) -->
    <rect x="90" y="700" width="150" height="55" rx="6" fill="#fff" stroke="#0078D4" stroke-width="2"/>
    <text x="165" y="722" text-anchor="middle" font-size="10" font-weight="bold" fill="#0078D4">📁 Storage Account</text>
    <text x="165" y="738" text-anchor="middle" font-size="9" fill="#666">&lt;unique-name&gt;</text>

    <!-- ACR (below pe-acr) -->
    <rect x="260" y="700" width="150" height="55" rx="6" fill="#fff" stroke="#0078D4" stroke-width="2"/>
    <text x="335" y="722" text-anchor="middle" font-size="10" font-weight="bold" fill="#0078D4">📦 Container Registry</text>
    <text x="335" y="738" text-anchor="middle" font-size="9" fill="#666">&lt;unique-name&gt;</text>

    <!-- Private DNS Zone - Blob (below Storage) -->
    <rect x="90" y="775" width="150" height="45" rx="6" fill="#fff" stroke="#107C10" stroke-width="2"/>
    <text x="165" y="795" text-anchor="middle" font-size="9" font-weight="bold" fill="#107C10">🔗 DNS: blob</text>
    <text x="165" y="810" text-anchor="middle" font-size="7" fill="#666">privatelink.blob.core.windows.net</text>

    <!-- Private DNS Zone - ACR (below ACR) -->
    <rect x="260" y="775" width="150" height="45" rx="6" fill="#fff" stroke="#107C10" stroke-width="2"/>
    <text x="335" y="795" text-anchor="middle" font-size="9" font-weight="bold" fill="#107C10">🔗 DNS: acr</text>
    <text x="335" y="810" text-anchor="middle" font-size="7" fill="#666">privatelink.azurecr.io</text>

    <!-- Log Analytics (far right, next to On-Prem legend area) -->
    <rect x="450" y="700" width="160" height="55" rx="6" fill="#fff" stroke="#5C2D91" stroke-width="2"/>
    <text x="530" y="722" text-anchor="middle" font-size="10" font-weight="bold" fill="#5C2D91">📊 Log Analytics</text>
    <text x="530" y="738" text-anchor="middle" font-size="9" fill="#666">laws-foundry-sbx</text>
  </g>

  <!-- ==================== On-Prem Simulation VNet (Right) ==================== -->
  <g id="onprem-vnet">
    <rect x="900" y="260" width="300" height="260" rx="8" fill="url(#onpremPurple)" stroke="#8661C5" stroke-width="2"/>
    <text x="1050" y="285" text-anchor="middle" font-size="13" font-weight="bold" fill="#8661C5">On-Prem Simulation VNet</text>
    <text x="1050" y="303" text-anchor="middle" font-size="10" fill="#666">vnet-onprem-sim-weu (10.7.1.0/24)</text>

    <!-- On-prem Subnet -->
    <rect x="920" y="320" width="260" height="180" rx="6" fill="#F5F0FF" stroke="#8661C5" stroke-width="1.5" stroke-dasharray="4,2"/>
    <text x="1050" y="340" text-anchor="middle" font-size="10" font-weight="bold" fill="#8661C5">snet-onprem-sim (10.7.1.0/24)</text>
    
    <!-- VM -->
    <rect x="950" y="355" width="200" height="85" rx="5" fill="#fff" stroke="#8661C5" stroke-width="2"/>
    <text x="1050" y="378" text-anchor="middle" font-size="10" font-weight="bold" fill="#8661C5">🖥️ vm-onprem-sim</text>
    <text x="1050" y="395" text-anchor="middle" font-size="9" fill="#666">Ubuntu 22.04 + nginx</text>
    <text x="1050" y="412" text-anchor="middle" font-size="9" fill="#888">IP: 10.7.1.4 | Ports: 80, 443</text>
    <text x="1050" y="432" text-anchor="middle" font-size="8" fill="#888">Simulates on-premises server</text>
    
    <!-- NSG -->
    <rect x="950" y="450" width="200" height="38" rx="4" fill="#F5F0FF" stroke="#8661C5" stroke-width="1"/>
    <text x="1050" y="468" text-anchor="middle" font-size="9" fill="#8661C5">🛡️ nsg-onprem-sim</text>
    <text x="1050" y="482" text-anchor="middle" font-size="8" fill="#888">Allow 80/443 from ACA subnet</text>
  </g>

  <!-- ==================== Connections ==================== -->
  
  <!-- Hub to Sandbox peering -->
  <line x1="530" y1="205" x2="400" y2="260" stroke="#107C10" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="410" y1="260" x2="540" y2="205" stroke="#107C10" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5,3"/>
  <rect x="420" y="210" width="95" height="32" rx="4" fill="#fff" stroke="#107C10" stroke-width="1"/>
  <text x="467" y="224" text-anchor="middle" font-size="7" fill="#107C10">peer-hub-to-sbx</text>
  <text x="467" y="236" text-anchor="middle" font-size="7" fill="#107C10">peer-sbx-to-hub</text>

  <!-- Hub to On-prem peering -->
  <line x1="670" y1="205" x2="970" y2="260" stroke="#8661C5" stroke-width="2" marker-end="url(#arrowhead)"/>
  <line x1="960" y1="260" x2="660" y2="205" stroke="#8661C5" stroke-width="2" marker-end="url(#arrowhead)" stroke-dasharray="5,3"/>
  <rect x="770" y="210" width="100" height="32" rx="4" fill="#fff" stroke="#8661C5" stroke-width="1"/>
  <text x="820" y="224" text-anchor="middle" font-size="7" fill="#8661C5">peer-hub-to-onprem</text>
  <text x="820" y="236" text-anchor="middle" font-size="7" fill="#8661C5">peer-onprem-to-hub</text>

  <!-- Sandbox to On-prem (Direct peering - horizontal in the gap) -->
  <line x1="630" y1="400" x2="900" y2="400" stroke="#E91E63" stroke-width="3" marker-end="url(#arrowhead)"/>
  <line x1="900" y1="420" x2="630" y2="420" stroke="#E91E63" stroke-width="3" marker-end="url(#arrowhead)"/>
  <rect x="710" y="370" width="100" height="35" rx="4" fill="#FCE4EC" stroke="#E91E63" stroke-width="1"/>
  <text x="760" y="384" text-anchor="middle" font-size="8" font-weight="bold" fill="#E91E63">Direct Peering</text>
  <text x="760" y="397" text-anchor="middle" font-size="7" fill="#E91E63">(Required for ACA!)</text>

  <!-- Storage to PE Blob (straight up) -->
  <line x1="165" y1="700" x2="165" y2="580" stroke="#FF8C00" stroke-width="1.5" stroke-dasharray="5,3" marker-end="url(#arrowhead)"/>
  
  <!-- ACR to PE ACR (straight up) -->
  <line x1="335" y1="700" x2="335" y2="580" stroke="#0078D4" stroke-width="1.5" stroke-dasharray="5,3" marker-end="url(#arrowhead)"/>

  <!-- Log Analytics to ACA (straight down from ACA, through PE subnet gap) -->
  <line x1="530" y1="700" x2="530" y2="660" stroke="#5C2D91" stroke-width="1.5" stroke-dasharray="4,2" marker-end="url(#arrowhead)"/>

  <!-- DNS Blob to VNet (straight up to bottom of VNet) -->
  <line x1="165" y1="775" x2="165" y2="755" stroke="#107C10" stroke-width="1" stroke-dasharray="3,3"/>
  
  <!-- DNS ACR to VNet (straight up) -->
  <line x1="335" y1="775" x2="335" y2="755" stroke="#107C10" stroke-width="1" stroke-dasharray="3,3"/>

  <!-- ==================== Legend (Right Side) ==================== -->
  <g id="legend" transform="translate(900, 550)">
    <rect x="0" y="0" width="550" height="400" rx="8" fill="#fff" stroke="#ddd" stroke-width="1"/>
    <text x="275" y="25" text-anchor="middle" font-size="13" font-weight="bold" fill="#333">Legend</text>
    
    <!-- Resource Groups -->
    <text x="20" y="55" font-size="10" font-weight="bold" fill="#333">Resource Groups:</text>
    <rect x="20" y="65" width="10" height="10" fill="#107C10" rx="2"/>
    <text x="38" y="74" font-size="9" fill="#666">rg-foundry-sbx-net (Networking)</text>
    <rect x="20" y="83" width="10" height="10" fill="#0078D4" rx="2"/>
    <text x="38" y="92" font-size="9" fill="#666">rg-foundry-sbx-app (ACA, Storage, ACR)</text>
    <rect x="20" y="101" width="10" height="10" fill="#FF8C00" rx="2"/>
    <text x="38" y="110" font-size="9" fill="#666">Hub VNet (Corporate simulation)</text>
    
    <!-- Connection Types -->
    <text x="20" y="140" font-size="10" font-weight="bold" fill="#333">Connections:</text>
    <line x1="20" y1="155" x2="60" y2="155" stroke="#107C10" stroke-width="2"/>
    <text x="70" y="159" font-size="9" fill="#666">VNet Peering (Hub ↔ Spoke)</text>
    <line x1="20" y1="173" x2="60" y2="173" stroke="#E91E63" stroke-width="3"/>
    <text x="70" y="177" font-size="9" fill="#666">Direct Peering (Spoke ↔ Spoke)</text>
    <line x1="20" y1="191" x2="60" y2="191" stroke="#FF8C00" stroke-width="1.5" stroke-dasharray="5,3"/>
    <text x="70" y="195" font-size="9" fill="#666">Private Endpoint Connection</text>
    <line x1="20" y1="209" x2="60" y2="209" stroke="#5C2D91" stroke-width="1.5" stroke-dasharray="4,2"/>
    <text x="70" y="213" font-size="9" fill="#666">Log Analytics / Diagnostics</text>
    
    <!-- IP Ranges -->
    <text x="300" y="55" font-size="10" font-weight="bold" fill="#333">IP Ranges:</text>
    <text x="300" y="73" font-size="9" fill="#666">Hub: 10.0.0.0/16</text>
    <text x="300" y="88" font-size="9" fill="#666">Sandbox: 10.7.0.0/26</text>
    <text x="310" y="103" font-size="9" fill="#666">├ ACA: 10.7.0.0/27</text>
    <text x="310" y="118" font-size="9" fill="#666">└ PE: 10.7.0.32/28</text>
    <text x="300" y="136" font-size="9" fill="#666">On-Prem: 10.7.1.0/24</text>
    
    <!-- Key Note -->
    <rect x="280" y="155" width="250" height="60" rx="4" fill="#FCE4EC" stroke="#E91E63" stroke-width="1"/>
    <text x="405" y="175" text-anchor="middle" font-size="9" font-weight="bold" fill="#E91E63">⚠️ Important</text>
    <text x="405" y="190" text-anchor="middle" font-size="8" fill="#666">VNet peering is non-transitive.</text>
    <text x="405" y="203" text-anchor="middle" font-size="8" fill="#666">Direct peering required for ACA → On-Prem</text>
    
    <!-- Private Endpoints -->
    <text x="20" y="245" font-size="10" font-weight="bold" fill="#333">Private Endpoints:</text>
    <text x="20" y="263" font-size="9" fill="#666">🔒 pe-blob - Storage Account (Blob)</text>
    <text x="20" y="279" font-size="9" fill="#666">🔒 pe-acr - Container Registry</text>
    <text x="20" y="295" font-size="9" fill="#666">🔑 id-aca-acr-pull - Managed Identity (AcrPull)</text>
    
    <!-- Terraform Info -->
    <text x="300" y="245" font-size="10" font-weight="bold" fill="#333">Terraform Modules:</text>
    <text x="300" y="263" font-size="8" fill="#666">📁 terraform/network - VNets, PE, ACR, VM</text>
    <text x="300" y="278" font-size="8" fill="#666">📁 terraform/aca_env - ACA Environment</text>
    <text x="300" y="293" font-size="8" fill="#666">📁 terraform/container_apps - Test Apps</text>
    
    <!-- Private DNS Zones -->
    <text x="20" y="325" font-size="10" font-weight="bold" fill="#333">Private DNS Zones:</text>
    <text x="20" y="343" font-size="9" fill="#666">🔗 privatelink.blob.core.windows.net</text>
    <text x="20" y="359" font-size="9" fill="#666">🔗 privatelink.azurecr.io</text>
    
    <!-- Project Info -->
    <text x="300" y="325" font-size="8" fill="#888">Enterprise Foundry</text>
    <text x="300" y="340" font-size="8" fill="#888">ACA Sandbox Setup</text>
    <text x="300" y="358" font-size="8" fill="#888">github.com/your-org/enterprise-foundry</text>
  </g>

</svg>
SVGEOF

echo "✅ Architecture diagram generated: $OUTPUT_FILE"
echo "   Open in a browser or VS Code to view the SVG"
