import React from 'react';

import InputField from 'app/views/settings/components/forms/inputField';

export default class NumberField extends React.Component {
  render() {
    return <InputField {...this.props} type="number" />;
  }
}
