import React from 'react';

import InputField from 'app/views/settings/components/forms/inputField';

export default class EmailField extends React.Component {
  render() {
    return <InputField {...this.props} type="email" />;
  }
}
