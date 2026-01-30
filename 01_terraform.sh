#!/usr/bin/env bash
set -euo pipefail

# ======= Terraform Module Executor =======
# Interactive script to deploy or destroy Terraform modules
# Handles dependencies and proper execution order

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/terraform"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'
BOLD='\033[1m'

# Module definitions (in dependency order for apply)
MODULES=("network" "aca_env" "container_apps")
MODULE_DESCRIPTIONS=(
    "network        - VNets, Peerings, VM, Storage, ACR, Private Endpoints"
    "aca_env        - Azure Container Apps Environment"
    "container_apps - Test Container Apps (on-prem & storage tests)"
)

# Required variables per module (variables without defaults)
declare -A MODULE_REQUIRED_VARS
MODULE_REQUIRED_VARS["network"]=""  # All have defaults
MODULE_REQUIRED_VARS["aca_env"]="subscription_id location rg_net rg_app vnet_name subnet_aca"
MODULE_REQUIRED_VARS["container_apps"]="subscription_id location rg_net rg_app aca_env_name storage_account_name"

# Track selected modules
declare -A SELECTED

print_header() {
    clear
    echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${CYAN}║${NC}  ${BOLD}🚀 Terraform Module Executor${NC}                              ${CYAN}║${NC}"
echo -e "${BOLD}${CYAN}║${NC}  Enterprise Foundry - ACA Sandbox Setup                      ${CYAN}║${NC}"
    echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

check_tfvars_variable() {
    local tfvars_file=$1
    local var_name=$2
    
    if [[ ! -f "$tfvars_file" ]]; then
        return 1
    fi
    
    # Check if variable is set (not commented, has a value)
    if grep -qE "^[[:space:]]*${var_name}[[:space:]]*=" "$tfvars_file"; then
        # Check it's not empty string
        local value=$(grep -E "^[[:space:]]*${var_name}[[:space:]]*=" "$tfvars_file" | head -1 | sed 's/.*=[[:space:]]*//' | tr -d '"' | tr -d "'" | xargs)
        if [[ -n "$value" ]]; then
            return 0
        fi
    fi
    return 1
}

check_module_parameters() {
    local module=$1
    local tfvars_file="$TF_DIR/$module/terraform.tfvars"
    local required_vars="${MODULE_REQUIRED_VARS[$module]}"
    local missing=()
    
    # If no required vars, return OK
    if [[ -z "$required_vars" ]]; then
        return 0
    fi
    
    # Check if tfvars file exists
    if [[ ! -f "$tfvars_file" ]]; then
        echo "terraform.tfvars not found"
        return 1
    fi
    
    # Check each required variable
    for var in $required_vars; do
        if ! check_tfvars_variable "$tfvars_file" "$var"; then
            missing+=("$var")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        echo "${missing[*]}"
        return 1
    fi
    
    return 0
}

print_modules() {
    echo -e "${BOLD}Available Modules:${NC}"
    echo ""
    for i in "${!MODULES[@]}"; do
        local module="${MODULES[$i]}"
        local status=""
        local param_status=""
        
        # Check selection
        if [[ "${SELECTED[$module]:-}" == "1" ]]; then
            status="${GREEN}[✓]${NC}"
        else
            status="[ ]"
        fi
        
        # Check parameters
        local missing=$(check_module_parameters "$module" 2>&1)
        if [[ $? -eq 0 ]]; then
            param_status="${GREEN}✓${NC}"
        else
            param_status="${RED}⚠ missing: $missing${NC}"
        fi
        
        echo -e "  $status ${BOLD}$((i+1)).${NC} ${MODULE_DESCRIPTIONS[$i]}"
        echo -e "         Parameters: $param_status"
    done
    echo ""
}

check_module_state() {
    local module=$1
    local state_file="$TF_DIR/$module/terraform.tfstate"
    
    if [[ -f "$state_file" ]] && [[ $(cat "$state_file" | grep -c '"type":') -gt 0 ]]; then
        echo "deployed"
    else
        echo "not_deployed"
    fi
}

print_status() {
    echo -e "${BOLD}Current Deployment Status:${NC}"
    echo ""
    for module in "${MODULES[@]}"; do
        local state=$(check_module_state "$module")
        if [[ "$state" == "deployed" ]]; then
            echo -e "  ${GREEN}●${NC} $module - ${GREEN}deployed${NC}"
        else
            echo -e "  ${YELLOW}○${NC} $module - ${YELLOW}not deployed${NC}"
        fi
    done
    echo ""
}

toggle_module() {
    local module=$1
    if [[ "${SELECTED[$module]:-}" == "1" ]]; then
        SELECTED[$module]="0"
    else
        SELECTED[$module]="1"
    fi
}

select_all() {
    for module in "${MODULES[@]}"; do
        SELECTED[$module]="1"
    done
}

select_none() {
    for module in "${MODULES[@]}"; do
        SELECTED[$module]="0"
    done
}

get_selected_modules() {
    local result=()
    for module in "${MODULES[@]}"; do
        if [[ "${SELECTED[$module]:-}" == "1" ]]; then
            result+=("$module")
        fi
    done
    echo "${result[@]:-}"
}

run_terraform() {
    local action=$1
    local module=$2
    local module_dir="$TF_DIR/$module"
    
    echo -e "\n${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Module: ${YELLOW}$module${NC} | Action: ${MAGENTA}$action${NC}"
    echo -e "${BOLD}${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
    
    cd "$module_dir"
    
    # Initialize if needed
    if [[ ! -d ".terraform" ]]; then
        echo -e "${YELLOW}Initializing Terraform...${NC}"
        terraform init
    fi
    
    if [[ "$action" == "apply" ]]; then
        terraform plan -out=tfplan
        echo ""
        read -p "Apply this plan? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform apply tfplan
            echo -e "\n${GREEN}✅ $module applied successfully${NC}"
        else
            echo -e "\n${YELLOW}⏭️  Skipped $module${NC}"
        fi
    elif [[ "$action" == "destroy" ]]; then
        terraform plan -destroy -out=tfplan
        echo ""
        read -p "Destroy these resources? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            terraform apply tfplan
            echo -e "\n${GREEN}✅ $module destroyed successfully${NC}"
        else
            echo -e "\n${YELLOW}⏭️  Skipped $module${NC}"
        fi
    elif [[ "$action" == "plan" ]]; then
        terraform plan
    fi
    
    cd "$SCRIPT_DIR"
}

execute_action() {
    local action=$1
    local selected=($(get_selected_modules))
    
    if [[ ${#selected[@]} -eq 0 ]]; then
        echo -e "${RED}No modules selected!${NC}"
        read -p "Press Enter to continue..."
        return
    fi
    
    # Validate parameters for selected modules (only for plan/apply)
    if [[ "$action" != "destroy" ]]; then
        local has_errors=false
        echo -e "\n${BOLD}Checking parameters...${NC}"
        for module in "${selected[@]}"; do
            local missing=$(check_module_parameters "$module" 2>&1)
            if [[ $? -ne 0 ]]; then
                echo -e "  ${RED}✗${NC} $module: missing ${RED}$missing${NC}"
                has_errors=true
            else
                echo -e "  ${GREEN}✓${NC} $module: all parameters set"
            fi
        done
        
        if [[ "$has_errors" == true ]]; then
            echo -e "\n${RED}Cannot proceed - missing required parameters!${NC}"
            echo -e "Edit the terraform.tfvars files in the respective module folders."
            read -p "Press Enter to continue..."
            return
        fi
    fi
    
    # For destroy, reverse the order
    if [[ "$action" == "destroy" ]]; then
        local reversed=()
        for ((i=${#selected[@]}-1; i>=0; i--)); do
            reversed+=("${selected[$i]}")
        done
        selected=("${reversed[@]}")
    fi
    
    echo -e "\n${BOLD}Execution Order:${NC}"
    for i in "${!selected[@]}"; do
        echo -e "  $((i+1)). ${selected[$i]}"
    done
    echo ""
    
    read -p "Continue with $action? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return
    fi
    
    for module in "${selected[@]}"; do
        run_terraform "$action" "$module"
    done
    
    echo -e "\n${BOLD}${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}  ✅ All selected modules processed!${NC}"
    echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════════════${NC}"
    read -p "Press Enter to continue..."
}

# Initialize selections
select_none

# Main menu loop
while true; do
    print_header
    print_status
    print_modules
    
    echo -e "${BOLD}Actions:${NC}"
    echo -e "  ${BOLD}1-3${NC}  Toggle module selection"
    echo -e "  ${BOLD}a${NC}    Select all"
    echo -e "  ${BOLD}n${NC}    Select none"
    echo -e "  ${BOLD}───────────────────────${NC}"
    echo -e "  ${BOLD}p${NC}    ${CYAN}Plan${NC} selected modules"
    echo -e "  ${BOLD}d${NC}    ${GREEN}Deploy (apply)${NC} selected modules"
    echo -e "  ${BOLD}x${NC}    ${RED}Destroy${NC} selected modules"
    echo -e "  ${BOLD}───────────────────────${NC}"
    echo -e "  ${BOLD}q${NC}    Quit"
    echo ""
    
    read -p "Choice: " -n 1 -r choice
    echo
    
    case $choice in
        1) toggle_module "network" ;;
        2) toggle_module "aca_env" ;;
        3) toggle_module "container_apps" ;;
        a|A) select_all ;;
        n|N) select_none ;;
        p|P) execute_action "plan" ;;
        d|D) execute_action "apply" ;;
        x|X) execute_action "destroy" ;;
        q|Q) 
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0 
            ;;
        *) 
            echo -e "${RED}Invalid choice${NC}"
            sleep 1
            ;;
    esac
done
