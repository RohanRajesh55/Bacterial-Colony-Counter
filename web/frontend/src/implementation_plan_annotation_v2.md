# Enhancing Annotation Editor with Class Selection

## Goal

Enable users to assign specific bacterial classes to bounding boxes and improve the editor layout.

## 1. AnnotationEditor Component Updates

- **Props**: Accept `classes` (list of names) and `colors` (mapping of class -> color).
- **State**: Add `selectedClass` state to track the currently active tool.
- **UI Layout**:
  - Switch to a **Sidebar + Canvas** layout.
  - **Sidebar**: Contains a list of classes as radio buttons/clickable chips.
  - **Canvas**: The existing image area.
- **Interaction**:
  - Clicking a class in the sidebar sets `selectedClass`.
  - New boxes are created with `selectedClass`.
  - Clicking an existing box selects it. Changing the class in the sidebar updates the selected box.

## 2. Style Updates

- Add sidebar styling.
- Add class-specific colors to bounding boxes (border color).

## 3. Integration

- Update `Admin.jsx` to pass the `classNames` and `classColors` to `AnnotationEditor`.
