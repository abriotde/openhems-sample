export default function({ parentElement, setStateValue, setTriggerValue, data}) {
    const container = parentElement.querySelector("#data-container");
    const node = data.node;
    const translate = data.translate;
    const img = data.img;
    const id = data.id;
    const isChecked = (node.duration > 0 || node.duration=="0");
    const display = (isChecked) ? "inline" : "none";
    const checked = (isChecked) ? "checked='checked'" : "";
    var duration = Math.floor(node.duration/60); // Keep only minutes, forget seconds.
    var duration_value;
    if (isChecked) {
        let min = duration%60;
        let hour = (duration-min)/60;
        duration_value=(""+hour).padStart(2,'0')+":"+(""+min).padStart(2,'0');
        // console.log("Duration:", duration)
    } else {
        duration_value="00:00";
    }
    container.innerHTML=`<div class="row device"><div class="col-25"><label for="${id}">${node.name}</label>
        <input type="checkbox" ${checked}>
        </div><div class="col-75">
        <span id="conf" style="display: ${display}">
            <span class="col-50">${img.hourglass}
                ${translate.for} <input type="time" title="${translate.tooltip_duration}" id="duration" name="duration" value="${duration_value}"">
            </span><span class="col-50">${img.alarm}
                ${translate.before} <span id="beforeDate">${node.date}</span>
                <input type="time" title="${translate.tooltip_timeout}" id="timeout" value="${node.timeout}" onchange="updateBeforeDate('${id}')">
            </span>
        </span></div></div>`;
    parentElement.querySelector("input[type=checkbox]").onclick = (event) => {
        const box = event.originalTarget;
        var vis = (box.checked) ? "inline" : "none";
        var row = box.parentElement.parentElement;
        // console.log("ShowMe(",box,") ", row);
        row.querySelector("#conf").style.display = vis;
        node.display = box.checked;
        setStateValue("node", node);
    };
    parentElement.querySelector("input#duration").onchange = (event) => {
        const durationVal = event.originalTarget.value;
        // console.log("changeDuration() ", input);
        var duration;
        if (durationVal=="" || durationVal=="00:00"){
            duration = 0;
        } else {
            const vals = durationVal.split(":");
            duration = parseInt(vals[0])*60 + parseInt(vals[1]);
        }
        node.duration = duration;
        setStateValue("node", node);
    }
    parentElement.querySelector("input#timeout").onchange = (event) => {
        const input = event.originalTarget;
        console.log("changeTimeout() ", input);
        node.timeout = input.value;
        setStateValue("node", node);
    }

}