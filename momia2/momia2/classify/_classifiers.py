from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestClassifier
import pandas as pd
import pickle as pk
from ..utils import *


class GenericClassifier:

    def __init__(self,
                 method='RandomForest',
                 existing_classifier=None,
                 **kwargs):

        self.model = None
        if method == 'RandomForest':
            self.model = RandomForestClassifier(**kwargs)
        if method == 'PretrainedModel' and existing_classifier is not None:
            self.model = existing_classifier(**kwargs)
        self.features = []
        self.method = method
        self.normalizer = StandardScaler()
        self.z_transform = False

    def train(self, training_df, test_size=0.4, random_state=33, verbose=True, normalize=False, **kwargs):

        # check feature presence
        _missing_features = []
        _features = []
        for f in self.features:
            if f not in training_df.columns:
                _missing_features.append(f)
            else:
                _features.append(f)

        if len(_missing_features) > 0 and verbose:
            print('The following features are not found in the training dataset: {}'.format(','.join(_missing_features)))
            self.features = _features

        # must have $annotation
        if '$annotation' not in training_df.columns:
            raise ValueError("Dataframe contains no '$annotation' for classification.")

        self.data = training_df[self.features].values
        self.data[np.where(np.isnan(self.data))] = 0
        if normalize:
            self.z_transform = True
            self.normalizer.fit(self.data)
            self.data = self.normalizer.transform(self.data)
        self.annotations = training_df['annotation'].values.reshape(-1, 1)

        # train test split
        self.X_train, \
        self.X_test, \
        self.Y_train, \
        self.Y_test = train_test_split(self.data, self.annotations, test_size=test_size, random_state=random_state)

        self.model.fit(self.X_train, self.Y_train.ravel())
        self.classification_score = self.model.score(self.X_test, self.Y_test.ravel())

        if verbose:
            print('Classification score using {} model is {}'.format(self.method, self.classification_score))

    def predict(self, target_df, probability=False):
        _missing_features = []
        for f in self.features:
            if f not in target_df.columns:
                _missing_features.append(f)
        if len(_missing_features) > 0:
            raise ValueError(
                'The following features are not found in the training dataset: {}'.format(','.join(_missing_features)))
        if len(target_df) == 0:
            raise ValueError('No data found!')
        data = target_df[self.features].values
        data = np.nan_to_num(data, copy=True, nan=0.0, posinf=0, neginf=0)
        if len(data) == 1:
            data = data.reshape(1, -1)
        if self.z_transform:
            data = self.normalizer.transform(data)
        if probability:
            return self.model.predict_proba(data)
        else:
            return self.model.predict(data)

    def update(self):
        return None





