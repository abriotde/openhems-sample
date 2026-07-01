export default function({ parentElement, setStateValue, setTriggerValue, data}) {
    const container = parentElement.querySelector("#data-container");
    const node = data.node;
    const translate = data.translate;
    const img = data.img;
    const id = data.id;
    const isChecked = (node.duration > 0);
    const display = (isChecked) ? "inline" : "none";
    const checked = (isChecked) ? "checked='checked'" : "";
    container.innerHTML=`<div class="row device"><div class="col-25"><label for="${id}">${node.name}</label>
        <input type="checkbox" ${checked}>
        </div><div class="col-75">
        <span id="conf" style="display: ${display}">
            <span class="col-50">${img.hourglass}
                ${translate.for} <input type="time" title="${translate.tooltip_duration}" id="duration" name="duration" value="${node.duration}"">
            </span><span class="col-50">${img.alarm}
                ${translate.before} <span id="beforeDate">${node.date}</span>
                <input type="time" title="${translate.tooltip_timeout}" id="timeout" value="${node.timeout}" onchange="updateBeforeDate('${id}')">
            </span>
        </span></div></div>`;
    parentElement.querySelector("input[type=checkbox]").onclick = (event) => {
        const box = event.originalTarget;
        var vis = (box.checked) ? "inline" : "none";
        var row = box.parentElement.parentElement;
        console.log("ShowMe(",box,") ", row);
        row.querySelector("#conf").style.display = vis;
        node.display = box.checked;
        setStateValue("node", node);
    };
    parentElement.querySelector("input#duration").onchange = (event) => {
        const input = event.originalTarget;
        console.log("changeDuration() ", input);
        node.duration = input.value;
        setStateValue("node", node);
    }
    parentElement.querySelector("input#timeout").onchange = (event) => {
        const input = event.originalTarget;
        console.log("changeTimeout() ", input);
        setStateValue("node", node);
    }

}