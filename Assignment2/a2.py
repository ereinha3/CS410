from imports import *

# Define hyperparameters
NUM_EPOCHS = 200

# Define the MLP Model
# This model definition was followed in accordance of slides on MLPs
class OneHiddenLayerMLP(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(OneHiddenLayerMLP, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

# Initialize models for each dataset
models = {
    'Cornell': OneHiddenLayerMLP(input_size=cornell[0].x.shape[1], hidden_size=64, output_size=torch.unique(cornell[0].y).shape[0]),
    'Texas': OneHiddenLayerMLP(input_size=texas[0].x.shape[1], hidden_size=64, output_size=torch.unique(texas[0].y).shape[0]),
    'Cora': OneHiddenLayerMLP(input_size=cora[0].x.shape[1], hidden_size=64, output_size=torch.unique(cora[0].y).shape[0]),
    'CiteSeer': OneHiddenLayerMLP(input_size=citeSeer[0].x.shape[1], hidden_size=64, output_size=torch.unique(citeSeer[0].y).shape[0])
}

# Initialize optimizers
optimizers = {
    'Cornell': torch.optim.Adam(models['Cornell'].parameters(), lr=0.001, weight_decay=5e-4),
    'Texas': torch.optim.Adam(models['Texas'].parameters(), lr=0.001, weight_decay=5e-4),
    'Cora': torch.optim.Adam(models['Cora'].parameters(), lr=0.001, weight_decay=5e-4),
    'CiteSeer': torch.optim.Adam(models['CiteSeer'].parameters(), lr=0.001, weight_decay=5e-4)
}

# Data splitting and masks
datasets = {'Cornell': cornell, 'Texas': texas, 'Cora': cora, 'CiteSeer': citeSeer}

# Arrays to store accuracies for each model
mlp_results = {name: {'train_accs': [], 'val_accs': [], 'test_accs': []} for name in datasets.keys()}

# Training loop
for epoch in range(NUM_EPOCHS):
    for name in datasets.keys():
        # Get model, optimizer and dataset from given name
        model = models[name]
        optimizer = optimizers[name]
        dataset = datasets[name][0]

        if (name == 'Texas' or name == 'Cornell'):
            # This was provided in the annonuncement and was super helpful!!!
            # I got stuck on this for quite a while before I saw the announcement
            dataset.train_mask = dataset.train_mask[:, 0]
            dataset.val_mask = dataset.val_mask[:, 0]   
            dataset.test_mask = dataset.test_mask[:, 0]

        model.train() # Set to training mode
        optimizer.zero_grad() # Initialize gradienst to 0
        out = model(dataset.x)  # Forward pass

        loss = F.nll_loss(out[dataset.train_mask], dataset.y[dataset.train_mask]) # Declare your loss function
        loss.backward() # Backward pass
        optimizer.step() # Update weights based on gradients from backward pass

        # Calculate accuracies
        with torch.no_grad():
            model.eval() # Set to eval mode
            pred = out.argmax(dim=1) # Get predictions
            # Find accuracies based off total number of correct predictions (0 if incorrect, 1 if correct -> sum and average)
            train_acc = (pred[dataset.train_mask] == dataset.y[dataset.train_mask]).float().mean()
            val_acc = (pred[dataset.val_mask] == dataset.y[dataset.val_mask]).float().mean()
            test_acc = (pred[dataset.test_mask] == dataset.y[dataset.test_mask]).float().mean()

        mlp_results[name]['train_accs'].append(train_acc.item())
        mlp_results[name]['val_accs'].append(val_acc.item())
        mlp_results[name]['test_accs'].append(test_acc.item())

print("\n--- Performance Comparison for MLP Node Classification ---")
for name in datasets.keys():
    print(f"{name}:")
    print(f"  Final Train Accuracy: {mlp_results[name]['train_accs'][-1]:.4f}")
    print(f"  Final Validation Accuracy: {mlp_results[name]['val_accs'][-1]:.4f}")
    print(f"  Final Test Accuracy: {mlp_results[name]['test_accs'][-1]:.4f}")
    print()

# Plotting the mlp_results
def plot_accuracies(mlp_results, datasets):
    plt.figure(figsize=(12, 8))
    for name in datasets.keys():
        plt.plot(mlp_results[name]['train_accs'], label=f'{name} Train Accuracy')
        plt.plot(mlp_results[name]['val_accs'], label=f'{name} Validation Accuracy')
        plt.plot(mlp_results[name]['test_accs'], label=f'{name} Test Accuracy')
    plt.xlabel('Epoch')
    plt.ylabel('Accuracy')
    plt.legend()
    plt.title('Accuracy over Epochs')
    plt.show()

plot_accuracies(mlp_results, datasets)


# CONCLUSION:
# Based on the performance, we can draw conclusions about the models:
# Very little hyperparameter tuning was done so we see validation accuracy follows a similar trend to test accuracy 
# We would expect the Cora and Citeseer dataset to have worse performance as the datasets are large (by about 20x) and therefore learn less information given the same number of epochs
# As we see, these models perform better than a random guess would be but large datasets (Cora and Citeseer) are still performing <50% accuracy 


from torch_geometric.utils import add_remaining_self_loops, degree
from torch_scatter import scatter

prop_results = {name: {'train_accs': [], 'val_accs': [], 'test_accs': []} for name in datasets.keys()}

def propagate(x, edge_index, edge_weight = None):
    # This will do feature propagation for a given graph based on adjacency matrix
    edge_index, _ = add_remaining_self_loops(edge_index, num_nodes=x.size(0))

    # Here we calculate the degree normalization term
    row, col = edge_index
    deg = degree(col, x.size(0), dtype=x.dtype)
    deg_inv_sqrt = deg.pow(-0.5)

    # For first order of approcimation of Laplacian matric in GCN, we use deg_inv_sqrt[row]*deg_inv_sqrt[col]
    if (edge_weight == None):
        edge_weight = deg_inv_sqrt[col] * deg_inv_sqrt[row]

    # Normalize the features on the starting point of the edge
    out = edge_weight.view(-1,1) * x[row]

    return scatter(out, edge_index[-1], dim=0, dim_size=x.size(0), reduce='add')

for name in datasets.keys():
    # Get model, optimizer and dataset from given name
    model = models[name]
    optimizer = optimizers[name]
    dataset = datasets[name][0]

    if (name == 'Texas' or name == 'Cornell'):
            # This was provided in the annonuncement and was super helpful!!!
            # I got stuck on this for quite a while before I saw the announcement
            dataset.train_mask = dataset.train_mask[:, 0]
            dataset.val_mask = dataset.val_mask[:, 0]   
            dataset.test_mask = dataset.test_mask[:, 0]

    one_hot_label = F.one_hot(dataset.y, num_classes=torch.unique(dataset.y).shape[0])
    one_hot_label[dataset.val_mask] = 0
    one_hot_label[dataset.test_mask] = 0
    
    pred = propagate(one_hot_label, dataset.edge_index)
    pred = pred.argmax(dim=1)

    train_acc = (pred[dataset.train_mask] == dataset.y[dataset.train_mask]).float().mean()
    test_acc = (pred[dataset.test_mask] == dataset.y[dataset.test_mask]).float().mean()
    val_acc = (pred[dataset.val_mask] == dataset.y[dataset.val_mask]).float().mean()

    mlp_results[name]['train_accs'].append(train_acc.item())
    mlp_results[name]['val_accs'].append(val_acc.item())
    mlp_results[name]['test_accs'].append(test_acc.item())

print("\n--- Performance Comparison for MLP Node Classification ---")
for name in datasets.keys():
    print(f"{name}:")
    print(f"  Final Train Accuracy: {mlp_results[name]['train_accs'][-1]:.4f}")
    print(f"  Final Validation Accuracy: {mlp_results[name]['val_accs'][-1]:.4f}")
    print(f"  Final Test Accuracy: {mlp_results[name]['test_accs'][-1]:.4f}")
    print()