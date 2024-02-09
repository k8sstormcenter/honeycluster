package main

import "github.com/sjwhitworth/golearn/base"

// Load the model
model, err := base.LoadModelFromFile("model.json")
if err != nil {
    return err
}

// In your transform function...
func doTransform(e transform.WriteEvent, w transform.RecordWriter) error {
    // Unmarshal the incoming message into a map
    var incomingMessage map[string]interface{}
    err := json.Unmarshal(e.Record().Value, &incomingMessage)
    if err != nil {
        return err
    }

    // Preprocess the data
    // ...

    // Make a prediction
    prediction, err := model.Predict(incomingMessage)
    if err != nil {
        return err
    }

    // Write the prediction to the output topic
    // ...
}