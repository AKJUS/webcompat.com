/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

/* Allows the user to enter description of the problem */

import $ from "jquery";
import notify from "../notify.js";
import { charsPercent } from "../utils.js";
import { showContainer } from "../ui-utils.js";

const MIN_CHARACTERS = 30;

const container = $(".step-container.step-description");
const MIN_CHAR_MODE = container.data("min-char");
const descriptionField = container.find("#steps_reproduce");
const progress = container.find(".problem-description .progress");
const bar = progress.find(".bar");
const nextStepButton = container.find(".next-description");

const handleNext = (event) => {
  event.preventDefault();
  notify.publish("showStep", { id: "screenshot" });
};

const setButtonState = (isDisabled) => {
  nextStepButton.prop("disabled", isDisabled);
};

const updateProgress = (percent) => {
  const isReady = percent === 100;

  bar.css("width", `${percent}%`);

  if (isReady) {
    progress.addClass("complete");
  } else {
    progress.removeClass("complete");
  }

  setButtonState(!isReady);
};

const onChange = (value) => {
  const percent = charsPercent(value, MIN_CHARACTERS);
  updateProgress(percent);
};

/*
  create the markdown with the URL of a newly uploaded
  image and add it to the bug description
*/
const updateDescription = (url) => {
  const imageURL = `<details>
      <summary>View the screenshot</summary>
      <img alt="Screenshot" src="${url}">
      </details>`;

  descriptionField.val((idx, value) => value + "\n" + imageURL);
};

const showProgress = () => {
  progress.removeClass("is-hidden");
  $(".char-limit").text(`Minimum ${MIN_CHARACTERS} characters`);
};

const initMinCharMode = () => {
  descriptionField.on("blur input", (event) => onChange(event.target.value));
  setButtonState(true);
  showProgress();
};

nextStepButton.on("click", handleNext);
if (MIN_CHAR_MODE) {
  initMinCharMode();
}

export default {
  show: () => {
    showContainer(container);
  },
  update: ({ url }) => {
    updateDescription(url);
  },
};
