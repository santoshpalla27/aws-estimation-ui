# Architecture Builder Design

## Tech Stack
-   **Library**: `reactflow` (standard, stable).
-   **Icons**: Using simple text/divs or `lucide-react` if available (will stick to standard emojis/text to avoid deps if needed, or check package.json).

## Data Model
### Node Data
```json
{
  "id": "node-1",
  "type": "serviceNode",
  "data": {
    "label": "EC2 Instance",
    "serviceId": "AmazonEC2", 
    "region": "us-east-1",
    "configuration": { "instanceType": "t3.micro", "storage": 30 },
    "cost": 12.45,
    "details": "t3.micro, 30GB gp3"
  },
  "position": { "x": 100, "y": 100 }
}
```

### Edge Data
Standard React Flow edges for visual connection (networking).

## UI Layout
-   **Left Sidebar**: "Service Palette". List of draggable services (EC2, S3, RDS, etc.).
-   **Center**: React Flow Canvas. Drop zone.
-   **Right Sidebar**: "Properties Panel". Shows inputs for the selected Node.
    -   When EC2 node selected -> Show Region, Instance Type, Storage inputs.
    -   Updates Node Data -> Recalculates Cost.
-   **Top Bar**: Total Cost display + Export Buttons.

## Implementation Steps
1.  **Install**: `npm install reactflow`
2.  **Components**:
    -   `ServiceNode.jsx`: Custom node component displaying Service Name, Icon, and Cost.
    -   `Builder.jsx`: Main container, handles drag-n-drop, state.
    -   `ConfigPanel.jsx`: The form to edit node attributes.
3.  **Integration**:
    -   Fetch pricing via our existing `/api/pricing` endpoints in the `ConfigPanel`.
