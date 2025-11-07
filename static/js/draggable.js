/**
 * Makes an HTML element draggable.
 * @param {HTMLElement} element The element to make draggable.
 * @param {Function} [onClick] An optional click handler to call if no drag occurs.
 */
function makeDraggable(element, onClick) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
    let isDragging = false;

    // Load position from localStorage
    const savedTop = localStorage.getItem('fab-top');
    const savedLeft = localStorage.getItem('fab-left');
    if (savedTop && savedLeft) {
        element.style.top = savedTop;
        element.style.left = savedLeft;
        element.style.right = 'auto';
        element.style.bottom = 'auto';
    } else {
        // Default position if none is saved
        element.style.right = '25px';
        element.style.bottom = '25px';
    }

    element.addEventListener('mousedown', dragMouseDown);

    function dragMouseDown(e) {
        // Only respond to left mouse button
        if (e.button !== 0) return;

        e.preventDefault();
        pos3 = e.clientX;
        pos4 = e.clientY;
        isDragging = false; // Reset flag

        document.addEventListener('mousemove', elementDrag);
        document.addEventListener('mouseup', closeDragElement);
    }

    function elementDrag(e) {
        isDragging = true;
        element.classList.add('dragging');
        
        e.preventDefault();
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;

        let newTop = Math.max(0, Math.min(element.offsetTop - pos2, window.innerHeight - element.offsetHeight));
        let newLeft = Math.max(0, Math.min(element.offsetLeft - pos1, window.innerWidth - element.offsetWidth));

        element.style.top = newTop + "px";
        element.style.left = newLeft + "px";
        element.style.right = 'auto'; // Ensure top/left positioning is used
        element.style.bottom = 'auto'; // Ensure top/left positioning is used
    }

    function closeDragElement() {
        document.removeEventListener('mousemove', elementDrag);
        document.removeEventListener('mouseup', closeDragElement);

        if (isDragging) {
            element.classList.remove('dragging');
            localStorage.setItem('fab-top', element.style.top);
            localStorage.setItem('fab-left', element.style.left);
        } else if (onClick) {
            // If we didn't drag, it's a click
            onClick();
        }
    }
}